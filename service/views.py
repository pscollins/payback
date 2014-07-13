import logging
import itertools

from flask import request, render_template, make_response, redirect, url_for,\
    flash, send_file, abort
from flask.ext.login import login_user, logout_user, current_user,\
    login_required
from payback.utils import easylogger

from payback.service.app import app, login_manager
# from engine.engine import TwilioClient, VenmoClient,\
#     TwilReq, SkyClient, FacebookUserClientBuilder, TaggedPhoto
from payback.engine import engine
from payback.service.models import Person, Bill


LOG = easylogger.LOG
twilio = engine.TwilioClient()
venmo = engine.VenmoClient()
sky = engine.SkyClient()
fb_builder = engine.FacebookUserClientBuilder()
upload_manager = engine.FileUploadManager()
# class InvalidFileError(Exception):
#     status_code = 400

DEBUG = False

# set up login manager
@app.login_manager.user_loader
def load_user(phone_number):
    return Person.objects(number=phone_number).first()


@app.route("/proc_file", methods=["GET", "POST"])
@login_required
def proc_file():
    add_training_imgs(request, current_user)
    flash("Added new image(s)!")
    return redirect(url_for('profile'))

def add_training_imgs(request_, user):
    files_dict = request_.files
    LOG.error("request: ", request.__dict__)
    LOG.error("len(files_dict)", len(files_dict))
    LOG.error("all files are: ", files_dict)
    LOG.debug("files are: ", files_dict.get("set").__dict__)

    for name in files_dict:
        LOG.debug("file name: ", name)

    sky.train_for_user(user, request.files.get("set"))
    # if manager.process(files_dict):

    return "SUCCESS"

def amount_str_to_float(amount_str, default=0.0):
    try:
        return float(amount_str)
    except ValueError:
        return default

def apply_bill_for(request_, amount_str):
    files_dict = request_.files

    LOG.debug("about to apply bill on ", files_dict)
    LOG.debug("for amount: ", amount_str)

    # assert len(files_dict) == 1

    nums_to_bill = sky.find_user_numbers_in(files_dict.get("to_ident"))

    # CAN WE DO THIS MORE ELEGANTLY????????
    # TODO: HANDLE THE CASE WHERE WE MATCH SOMEONE WHO DOESN'T EXIST,
    # REMOVE DUPLICATE PERSON MATCHES
    users_to_bill = [Person.objects(number=num)[0]
                     for num in nums_to_bill]

    # try:
    #     amount = float(amount_str)
    # except ValueError:
    #     amount = 0.0

    amount = amount_str_to_float(amount_str)

    # me = user_from_cookies(request.cookies)
    if len(users_to_bill) == 0:
        flash('Cannot find any faces')
        return 0

    amt_per_person = amount/len(users_to_bill)

    LOG.debug("me: ", current_user)
    LOG.debug("me.__dict__", current_user.__dict__)

    # ADD IN CHECK SO YOU DON'T BILL ME
    for user in users_to_bill:
        bill = Bill(from_=current_user.id, to=user,
                    amount=float(amt_per_person))
        bill.save()
        twilio.send_auth_text(bill)

    return len(users_to_bill)

def flash_conf_message(users_billed):
    flash('Sent a bill to {}.'.format(", ".join([u.name for u in
                                                 users_billed])))

@app.route("/outstanding", methods=["GET"])
@login_required
def outstanding():
    bills_you_owe = engine.find_bills_from(current_user.id)
    bills_owed_to_you = engine.find_bills_to(current_user.id)

    return render_template("outstanding.html",
                           bills_you_owe=bills_you_owe,
                           bills_owed_to_you=bills_owed_to_you)


def find_not_me_name(bill):
    if bill.to.name == current_user.name:
        return bill.from_.name
    else:
        return bill.to.name


@app.route("/pay_outstanding", methods=["POST"])
@login_required
def pay_outstanding():
    LOG.debug("bills you want to pay:", request.form)
    people_concerned = []

    for key, value in request.form.items():
        action, id_ = key.split("|")

        # not clear what (if anything) we ever get sent for an
        # unchecked box. assuming that 'value' needs to be truthy.
        if value:
            bill = Bill.objects(id=id_).first()
            if action == "pay":
                venmo.pay_bill(bill)
            if action == "cancel" or action == "pay":
                people_concerned.append(find_not_me_name(bill))
                bill.delete()
            else:
                abort(404)

    flash("Resolved bills with {}.".format(",".join(people_concerned)))

    return redirect(url_for("profile"))

@app.route("/mobile", methods=["GET"])
@login_required
def render_simple_upload():
    return render_template("simple_upload.html")

@app.route("/images/<identifier>", methods=["GET"])
@login_required
def serve_image(identifier):
    # this is DEFINITELY DEFINITELY DEFINITELY A SECURITY RISK AND
    # SOMETHING NEEDS TO BE DONE TO FIX IT later on
    if upload_manager.image_exists(identifier):
        path = upload_manager.path_from_hash_for_send_file(identifier)
        LOG.debug("trying to send file. Path: ", path)

        return send_file(path)
    else:
        LOG.debug('aborting')
        abort(404)

@app.route("/confirm_bill", methods=["POST"])
@login_required
def confirm_bill():
    file_ = request.files.get("to_ident")
    amount = amount_str_to_float(request.form.get("amount"))

    taggedphoto = sky.taggedphoto_from_image(file_)

    LOG.debug("got tags: ", taggedphoto.tags)

    users = engine.TaggedUsers.from_taggedphoto(taggedphoto)

    default_amount = amount / (users.count() or 1)

    cutout_paths_and_users = []

    # THESE ARE ACTUALLY TAGGEDPHOTOS, NOT USERS
    for cutout, users in users.get_cutouts_and_users():
        LOG.debug("cutout: ", cutout)
        LOG.debug("users: ", users)
        cutout_path = upload_manager.build_temp_file(cutout)

        user_records = []

        # DO SOME ERROR HANDLING HERE LATER
        for user in users:
            user_records.append(Person.objects(number=user.number).first())

        cutout_paths_and_users.append((cutout_path, user_records))

    LOG.debug("about to pass to template: ", cutout_paths_and_users)
    return render_template("confirm_bill.html",
                           cutout_paths_and_users=cutout_paths_and_users,
                           default_amount="{:.2f}".format(default_amount))

@app.route("/apply_bill", methods=["POST"])
@login_required
def apply_bill():
    # This is probably a security risk.
    LOG.debug("got form: ", request.form)
    users_billed = []

    for el in itertools.count(start=1):
        person_number = request.form.get("person|{}".format(el))

        if not person_number:
            break
        # we should do javascripty things here
        elif person_number == "noone":
            continue

        LOG.debug("got person_number: ", person_number)

        amount = amount_str_to_float(request.form.get("amount|{}".format(el)))
        to_bill = Person.objects(number=person_number).first()
        # .id?????
        bill = Bill(to=current_user.id,
                    from_=to_bill,
                    amount=amount)
        bill.save()
        twilio.send_auth_text(bill)
        users_billed.append(to_bill)

    flash_conf_message(users_billed)

    return redirect(url_for('profile'))

# CURRENTLY *NOT* GETTING HIT
@app.route("/mobile_upload", methods=["POST"])
@login_required
def apply_uploaded_file():
    LOG.debug("forwarding request: ", request)
    LOG.debug("request.data: ", request.data)
    LOG.debug("request.__dict__", request.__dict__)
    amount = request.form.get("amount")
    LOG.debug("amount: ", amount)

    apply_bill_for(request, amount)

    return redirect(url_for('profile'))

# endpoint for mobile to hit
@app.route("/venmo_auth_url", methods=["GET"])
def venmo_auth_url():
    return {"url": venmo.get_auth_url()}

@app.route("/", methods=["GET"])
def render_login():
    if current_user.is_authenticated():
        return redirect(url_for('profile'))

    return render_template("index.html",
                           register_url=venmo.get_auth_url())

@app.route("/text_recv", methods=["GET"])
def receive_text():
    params = request.args
    LOG.debug("got request: ", request)
    LOG.debug("request.args: ", request.args)
    twilreq = engine.TwilReq(params.get("From").strip("+"), params.get("Body"))

    person_billed, bills = twilio.process_twilreq(twilreq)

    if person_billed is not None:
        venmo.make_payments(person_billed, [b.to for b in bills])
        resp = twilio.payment_conf(person_billed, bills)
    else:
        resp = twilio.payment_rej()

    for bill in bills:
        bill.delete()

    return resp


def login_existing(person):
    '''
    Given a user that we recognize, redirect her to her profile.
    '''

    flash("Welcome back!")
    login_user(person)

    return redirect(url_for('profile'))


def create_new(person):
    '''
    Commit a new user to the database and prompt for Facebook credentials.
    '''

    person.save()
    login_user(person)

    flash('Thanks for registering!')

    return redirect(url_for('register_new'))


@app.route("/register_new", methods=["GET"])
@login_required
def register_new():
    return render_template("register_new.html")


@app.route("/facebook_signup", methods=["POST"])
@login_required
def facebook_signup():
    add_training_imgs(request, current_user)

    # Not sure what scope we want here
    return render_template("facebook_signup.html")

@app.route("/process_facebook_signup", methods=["GET"])
@login_required
def process_facebook_signup():
    # NOW WE LEARN THEIR MOST RECENT PICTURES,
    # AND MAYBE WE THROW AND ERROR IF THEY DON'T HAVE ENOUGH
    access_token = request.args['accessToken']

    fb_user = fb_builder.client_for_person(current_user, access_token)

    tagged_photos = fb_user.get_photos()

    LOG.debug("Got photos: ", tagged_photos)

    LOG.debug("Got tagged photos: ", tagged_photos)
    LOG.debug("About to submit to SkyBiometry...")

    sky.train_for_facebook(current_user, tagged_photos)

    return redirect(url_for("profile"))


@app.route("/code_recv", methods=["GET"])
def process_venmo_code():
    '''
    Use the code given to us by the Venmo authentication to see if
    we're dealing with a new user or an existing one
    '''
    auth_code = request.args.get("code")

    LOG.debug("auth_code: ", auth_code)

    new_person = venmo.person_from_auth_code(auth_code)
    old_person = Person.objects(number=new_person.number).first()
    if old_person and not DEBUG:
        return login_existing(old_person)
    else:
        return create_new(new_person)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('render_login'))


# def user_from_cookies(cookies):
#     usernum = cookies.get("usernum")
#     return Person.objects(number=usernum)[0]


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        #me = user_from_cookies(request.cookies)
        add_training_imgs(request, current_user)

        flash('images added.')

    if current_user.is_authenticated():
        name = current_user.name
    else:
        name = 'Stranger'
    return render_template("my_profile.html", username=name)


if __name__ == "__main__":
    app.run(host='0.0.0.0')
