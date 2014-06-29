import logging

from flask import Flask, request

from manager import Manager
from utils import easylogger
from service import app
from engine.engine import Engine, TwilReq

manager = Manager()
LOG = easylogger.LOG
engine = Engine()
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
    return "Authorize with Paypal: {}".format(engine.get_login_url)

@app.route("/text_recv", methods=["GET"])
def recieve_text():
    params = request.args
    twilreq = TwilReq(params.get("From"), params.get("Body"))

    return engine.process_twilreq(twilreq)


if __name__ == "__main__":
    app.run()
