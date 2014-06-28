import logging

from flask import Flask, request

from manager import Manager
from utils import easylogger
from service import app


# app = Flask(__name__)
manager = Manager()
LOG = easylogger.LOG
# class InvalidFileError(Exception):
#     status_code = 400

@easylogger.log_at(logging.DEBUG)
@app.route("/", methods=["GET", "POST"])
def main():
    if request.method == "POST":
        files_dict = request.files
        LOG.error("request: ", request.__dict__)
        LOG.error("len(files_dict)", len(files_dict))
        for name in files_dict:
            LOG.error("file name: ", files.dict)

        if manager.process(files_dict):
            return "SUCCESS"

    raise AttributeError



if __name__ == "__main__":
    app.run()
