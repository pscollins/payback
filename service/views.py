import logging
# import requests

from flask import request, render_template, make_response, redirect, url_for,\
    flash
from flask.ext.login import login_user, logout_user, current_user,\
    login_required
from manager import Manager
from utils import easylogger
from service import app, login_manager
from engine.engine import TwilioClient, VenmoClient, TwilReq, SkyClient, \
    FacebookUserClientBuilder
from models import Person, Bill


manager = Manager()
LOG = easylogger.LOG
twilio = TwilioClient()
venmo = VenmoClient()
sky = SkyClient()
fb_builder = FacebookUserClientBuilder()
# class InvalidFileError(Exception):
#     status_code = 400

DEBUG = True

# set up login manager
@login_manager.user_loader
def load_user(phone_number):
    return Person.objects(number=phone_number).first()


@app.route("/proc_file", methods=["GET", "POST"])
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

    try:
        amount = float(amount_str)
    except ValueError:
        amount = 0.0

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

    flash('Sent a bill to {}.'.format(", ".join([u.name for u in
                                                 users_to_bill])))
    return len(users_to_bill)

@app.route("/mobile", methods=["GET"])
@login_required
def render_simple_upload():
    return render_template("simple_upload.html")

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
    twilreq = TwilReq(params.get("From").strip("+"), params.get("Body"))

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
    access_token = request.args()['accessToken']

    fb_user = fb_builder(current_user, access_token)

    photos = fb_user.get_photos()

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
