from flask import render_template
from flask_mail import Message
from sqlalchemy import Date
from drivercompletion import db, mail
from drivercompletion.models import( 
    Orders, 
    Employees,
    ClientMaster,
    Terminals, 
    OrderDrivers)
from drivercompletion.config import config
from datetime import datetime, date

import os
import csv
import xlsxwriter


def get_non_complete_count(): 
    non_complete_count = db.session.query(Orders.OrderTrackingID, ClientMaster.ClientID, OrderDrivers.DriverID)
    non_complete_count = non_complete_count.join(OrderDrivers, Orders.OrderTrackingID == OrderDrivers.OrderTrackingID)
    non_complete_count = non_complete_count.join(ClientMaster, ClientMaster.ClientID == Orders.ClientID)
    return non_complete_count

def get_completed_count(): 
    complete_count = db.session.query(OrderDrivers.OrderTrackingID, Orders.ClientID, ClientMaster.ClientID)
    complete_count = complete_count.join(Orders, OrderDrivers.OrderTrackingID == Orders.OrderTrackingID)
    complete_count = complete_count.join(ClientMaster, ClientMaster.ClientID == Orders.ClientID)
    return complete_count

def get_uncomplete_count(employee_id):
    today = datetime.today()
    today = today.date()
    non_complete_count = get_non_complete_count()
    response = non_complete_count.filter(
        OrderDrivers.DriverID == employee_id, 
        Orders.Status == 'N',
        Orders.DeliveryTargetTo.cast(Date) == today)
    response = len(response.all())
    return response


def get_complete_count(employee_id):
    today = datetime.today()
    today = today.date()
    status_list = ['N', 'D', 'L']
    complete_count = get_completed_count()
    response = complete_count.filter(
        OrderDrivers.DriverID == employee_id, 
        ~Orders.Status.in_(status_list),
        Orders.DeliveryTargetTo.cast(Date) == today)
    response = len(response.all())
    return response


def get_driver_report():
    try:
        driver_complete = db.session.query(Terminals.TerminalID, Terminals.TerminalName, Employees.ID, Employees.DriverNo, Employees.LastName, Employees.FirstName)
        driver_complete = driver_complete.join(Terminals, Employees.TerminalID == Terminals.TerminalID)
        driver_complete = driver_complete.filter(Employees.Status == 'A', Employees.Driver == 'Y', Employees.DriverType == 'C')
        driver_complete = driver_complete.order_by(Terminals.TerminalName)
        driver_complete = driver_complete.all()

        drivers = [r._asdict() for r in driver_complete]
        summary ={}
        total_summary ={
            'active': 0, 
            'complete': 0, 
            'total': 0,
            'percent_complete': 0, 
            'name': 'Total'
        }
        summary = {}
        for driver in drivers:
            uncompleted = get_uncomplete_count(driver['ID'])
            completed = get_complete_count(driver['ID'])
            driver['Uncompleted'] = uncompleted
            driver['Completed'] = completed
            terminal = driver['TerminalName']
            if terminal in summary:
                summary[terminal]['active'] += int(uncompleted)
                summary[terminal]['complete'] += int(completed)
                summary[terminal]['total'] += int(completed) + int(uncompleted)
            else:
                summary[terminal] = {}
                summary[terminal]['active'] = int(uncompleted)
                summary[terminal]['complete'] = int(completed)
                summary[terminal]['name'] = terminal
                summary[terminal]['total'] = int(completed) + int(uncompleted)
            total_summary['active'] += int(uncompleted)
            total_summary['complete'] += int(completed)
            total_summary['total'] += int(completed) + int(uncompleted)
            if summary[terminal]['total'] > 0:
                summary[terminal]['percent_complete'] = round((summary[terminal]['complete']/summary[terminal]['total']) * 100, 2) 
            if total_summary['total'] > 0:
                total_summary['percent_complete'] = round((total_summary['complete']/total_summary['total']) * 100, 2) 
            
        # return {'drivers': drivers, 'count': len(drivers), 'summary': summary, 'total': total_summary}
        today = date.today()
        today = today.strftime("%m_%d_%y")
        file_name = 'Driver_Completion_Report-' + today + '.xlsx'
        workbook = xlsxwriter.Workbook(file_name)
        worksheet = workbook.add_worksheet()
        now = datetime.now()
        date_time = now.strftime("%m/%d/%Y, %H:%M:%S")
            

        headers = ['Terminal Name',  'Driver NO', 'Last Name', 'First Name', 'Uncompleted', 'Completed', '% Completed']
        for x in range(len(headers)):
            worksheet.write(0, x, headers[x])
        
        for idx, driver in enumerate(drivers):
            
            if (int(driver['Uncompleted'])+int(driver['Completed'])) >0:
                worksheet.write(idx+1, 0, driver['TerminalName'])
                worksheet.write(idx+1, 1, driver['DriverNo'])
                worksheet.write(idx+1, 2, driver['LastName'])
                worksheet.write(idx+1, 3, driver['FirstName'])
                worksheet.write(idx+1, 4, driver['Uncompleted'])
                worksheet.write(idx+1, 5, driver['Completed'])
                divisor = (driver['Completed'] + driver['Uncompleted'])
                if divisor > 0:
                    per = str(round((driver['Completed']/divisor) * 100, 2))
                    per = per + ' %'
                    worksheet.write(idx+1, 6, per )
                else:
                    worksheet.write(idx+1, 6, '0.00 %')

        workbook.close()

        

        subject = 'Driver Completion Report - ' + today
        msg = Message(
                        sender=str(config.EMAIL),
                        subject=subject,
                        recipients = config.RECIPIENTS
                    )

        msg.html = render_template('driver_report.html', day_of_report=date_time, total_summary=total_summary, summary=list(summary.values()))
        file = open(file_name, 'rb')

        
        msg.attach(file_name, '	application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', file.read())
        mail.send(msg)

        return render_template('success.html')
    except Exception as e:
        print(e)
        return render_template('error.html')