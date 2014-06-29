import logging
import requests

from flask import Flask, request, render_template

from manager import Manager
from utils import easylogger
from service import app#, db
from engine.engine import TwilioClient, VenmoClient, TwilReq

manager = Manager()
LOG = easylogger.LOG
twilio = TwilioClient()
venmo = VenmoClient()
# class InvalidFileError(Exception):
#     status_code = 400



@easylogger.log_at(logging.DEBUG)
@app.route("/proc_file", methods=["GET", "POST"])
def proc_file():
    if request.method == "POST":
        files_dict = request.files
        LOG.error("request: ", request.__dict__)
        LOG.error("len(files_dict)", len(files_dict))
        for name in files_dict:
            LOG.error("file name: ", name)

        if manager.process(files_dict):
            return "SUCCESS"

    raise AttributeError

@app.route("/", methods=["GET"])
def render_login():
    return render_template("index.html",
                           register_url=venmo.get_auth_url())

@app.route("/text_recv", methods=["GET"])
def receive_text():
    params = request.args
    twilreq = TwilReq(params.get("From"), params.get("Body"))

    bills, person_billed = twilio.process_twilreq(twilreq)

    venmo.make_payments(person_billed, [b.to for b in bills])

    return twilio.payment_conf(person_billed, bills)

@app.route("/code_recv", methods=["GET"])
def register_user():
    auth_code = requests.args.get("code")

    LOG.debug("auth_code: ", auth_code)

    person = venmo.person_from_auth_code(auth_code)

    # COMMIT PERSON TO DB
    person.save()

    # RETURN SOME "SUCESSFULLY REGISTERED" MESSAGE
    return ""



if __name__ == "__main__":
    app.run()
