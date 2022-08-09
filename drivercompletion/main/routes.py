from flask import render_template, request, Blueprint
from drivercompletion.api_func.report import get_driver_report


main = Blueprint('main', __name__)


@main.route("/")
@main.route("/home")
def home():
    return render_template('home.html')

@main.route("/report", methods=["GET", "POST"])
def get_report():
    return get_driver_report()
    
    

