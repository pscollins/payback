import logging
# import requests

from flask import Flask, request, render_template, make_response

from manager import Manager
from utils import easylogger
from service import app#, db
from engine.engine import TwilioClient, \
     VenmoClient, TwilReq, SkyClient
from models import Person, Bill

manager = Manager()
LOG = easylogger.LOG
twilio = TwilioClient()
venmo = VenmoClient()
sky = SkyClient()
# class InvalidFileError(Exception):
#     status_code = 400



# @easylogger.log_at(logging.DEBUG)
# @app.route("/proc_file", methods=["GET", "POST"])
def add_training_imgs(request_, user):
    files_dict = request_.files
    LOG.error("request: ", request.__dict__)
    LOG.error("len(files_dict)", len(files_dict))
    for name in files_dict:
        LOG.debug("file name: ", name)

    sky.train_for_user(user, request.files)
    # if manager.process(files_dict):

    return "SUCCESS"

def apply_bill_for(request_, amount):
    files_dict = request_.files

    LOG.debug("about to apply bill on ", files_dict.__dict)
    LOG.debug("for amount: ", amount)

    # assert len(files_dict) == 1

    nums_to_bill = sky.find_user_numbers_in(files_dict.get("SOMEKEY???"))

    # CAN WE DO THIS MORE ELEGANTLY????????
    users_to_bill = [Person.objects(number=num)[0]
                     for num in nums_to_bill]

    me = user_from_cookies(request.cookies)
    amt_per_person = amount/len(users_to_bill)

    # ADD IN CHECK SO YOU DON'T BILL ME
    for user in users_to_bill:
        bill = Bill(to=me, from_=user, amount=amt_per_person)
        bill.save()
        twilio.send_auth_text(bill)

    # RETURN SOME SUCCESS INDICATOR
    return ""

@app.route("/mobile", methods=["GET"])
def render_simple_upload():
    return render_template("simple_upload.html")

@app.route("/mobile_upload", methods=["POST"])
def apply_uploaded_file():
    LOG.debug("forwarding request: ", request)
    amount = request.data.get("amount")
    LOG.debug("amount: ", amount)

    return apply_bill_for(request, amount)

@app.route("/", methods=["GET"])
def render_login():
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
        return twilio.payment_conf(person_billed, bills)
    else:
        return twilio.payment_rej()

@app.route("/code_recv", methods=["GET"])
def register_user():
    auth_code = request.args.get("code")

    LOG.debug("auth_code: ", auth_code)

    person = venmo.person_from_auth_code(auth_code)

    # COMMIT PERSON TO DB
    person.save()

    resp = make_response(render_template("my_profile.html",
                                        success_message="Welcome!"))

    # set cookie so we can later know who uploads the file
    resp.set_cookie("usernum", person.number)


    # RETURN "SUCESSFULLY REGISTERED" TEMPLATE
    return resp

def user_from_cookies(cookies):
    usernum = cookies.get("usernum")
    return Person.objects(number=usernum)[0]

@app.route("/profile", methods=["GET", "POST"])
def profile():
    if request.method == "POST":
        me = user_from_cookies(request.cookies)
        add_training_imgs(me, request)

        # FLASH HERE OR WHATEVER

    return render_template("my_profile.html")


if __name__ == "__main__":
    app.run(host='0.0.0.0')
