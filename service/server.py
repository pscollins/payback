import logging

from flask import Flask, request, render_template

from manager import Manager
from utils import easylogger
from service import app, db
from engine.engine import Twilio, Venmo

manager = Manager()
LOG = easylogger.LOG
twilio = Twilio()
venmo = Venmo()
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
    return "Authorize with Paypal: {}".format(twilio.get_login_url())

@app.route("/text_recv", methods=["GET"])
def receive_text():
    params = request.args
    twilreq = TwilReq(params.get("From"), params.get("Body"))

    return twilio.process_twilreq(twilreq)

@app.route("/code_recv", methods=["GET"])
def register_user():
    auth_code = requests.args.get("code")

    LOG.debug("auth_code: ", auth_code)

    person = venmo.person_from_auth_code(auth_code)

    # COMMIT PERSON TO DB

    # RETURN SOME "SUCESSFULLY REGISTERED" MESSAGE
    return ""



if __name__ == "__main__":
    app.run()
