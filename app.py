from flask import Flask, jsonify, make_response, render_template, request, redirect, url_for, session
from pymysql import connections
import os
import boto3
import secrets
from config import *
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)  # You can adjust the length as needed
bucket = custombucket
region = customregion

db_conn = connections.Connection(
    host=customhost,
    port=3306,
    user=customuser,
    password=custompass,
    db=customdb

)
output = {}
table_admin = 'admin'


@app.route("/", methods=['GET', 'POST'])
def index():
    return render_template('index.html')


@app.route("/about", methods=['GET','POST'])
def about():
    return render_template('about.html')

@app.route("/company", methods=['GET','POST'])
def company():
    comp_id = request.args.get('company_id')
    cursor = db_conn.cursor()
    select_company_sql = "SELECT * FROM company WHERE comp_id=%s"
    cursor.execute(select_company_sql,(comp_id,))
    company = cursor.fetchone()

    select_job_sql = "SELECT * FROM Job WHERE comp_id = %s"
    cursor.execute(select_job_sql, (comp_id,))
    jobs = list(cursor.fetchall())
    try:
            # Initialize lists to store job offers and allowances
            job_offers = []
            allowances = []

            # Loop through the form fields and check for non-empty values
            for i in range(1, 4):  # Adjust the range based on the number of fields
                job_offer_field = request.form.get(f"job_offer_{i}")
                allowance_field = request.form.get(f"allowance_{i}")

                # Check if the fields have values
                if job_offer_field and allowance_field:
                    job_offers.append(job_offer_field)
                    
                    # Convert allowance_field to a numeric type (e.g., float)
                    allowance = float(allowance_field)
                    allowances.append(allowance)
                    
                    # Update the allowance for the corresponding job
                    jobs[i - 1]['allowance'] = allowance

            # Determine the range of allowances
            min_allowance = min(allowances) if allowances else None
            max_allowance = max(allowances) if allowances else None
    except Exception as e:
        return str(e)
    max_jobs = 3
    for _ in range(len(jobs), max_jobs):
        jobs.append((" ", " "))  # Add empty values for missing jobs

    
    select_internship_sql = "SELECT * FROM internship WHERE comp_id = %s"
    cursor.execute(select_internship_sql, (comp_id,))
    internships = cursor.fetchall()  # Fetch all internships supervised by this supervisor
    
 
 # Initialize an empty list to store student details
    students = []

    # Loop through each internship to fetch student details
    for internship in internships:
        select_student_sql = "SELECT * FROM student WHERE stud_id = %s"
        cursor.execute(select_student_sql, (internship[1],))
        student = list(cursor.fetchone())  # Convert the student tuple into a list

        # Add the internship details to the student data
        student.append(internship[4])  # Job Position
        student.append(internship[5])  # Allowance
        student.append(internship[7])  # Grade
        student.append(internship[8])  # Status
        students.append(student)  # Append student data to the list

    if request.method == 'POST':
        try:
            student_id = request.form['stud_id']
            new_status = request.form['statusDropdown']

            # Update the status in the database using student_id and new_status
            # Implement your database update logic here
            cursor = db_conn.cursor()
            update_status_sql = "UPDATE internship SET status=%s WHERE stud_id = %s"
            cursor.execute(update_status_sql, (new_status, student_id,))
            db_conn.commit()

            comp_id = session.get('user_id')  # Get supervisor ID from the session
            cursor = db_conn.cursor()
            select_internship_sql = "SELECT * FROM internship WHERE comp_id = %s"
            cursor.execute(select_internship_sql, (comp_id,))
            internships = cursor.fetchall()  # Fetch all internships supervised by this supervisor

                    # Initialize an empty list to store student details
            students = []

            # Loop through each internship to fetch student details
            for internship in internships:
                select_student_sql = "SELECT * FROM student WHERE stud_id = %s"
                cursor.execute(select_student_sql, (internship[1],))
                student = list(cursor.fetchone())  # Convert the student tuple into a list

                # Add the internship details to the student data
                student.append(internship[4])  # Job Position
                student.append(internship[5])  # Allowance
                student.append(internship[7])  # Grade
                student.append(internship[8])  # Status
                students.append(student)  # Append student data to the list

        except Exception as e:
            # Handle errors and render an HTML page with an error message
            return str(e)
    response = make_response(render_template('company.html', company=company, jobs=jobs, min_allowance=min_allowance, max_allowance=max_allowance, students=students))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response
    #return render_template('company.html', company = company, jobs=jobs, min_allowance = min_allowance, max_allowance = max_allowance, students = students)


@app.route("/admin", methods=['GET','POST'])
def admin():
    admin_id = request.args.get('admin_id')
    success_message = None 
    cursor = db_conn.cursor()
    select_company_sql = "SELECT * FROM company"
    cursor.execute(select_company_sql)
    companies = cursor.fetchall()
    return render_template('admin.html', companies = companies,success_message=success_message)

@app.route("/add_comp", methods=['GET','POST'])
def add_comp():
    success_message = None 
    if request.method == 'POST':
        cursor = db_conn.cursor()
        company_name = request.form['company_name']
        phone_number = request.form['phone_number']
        address = request.form['address']
        background = request.form['background']
        password = request.form['password']
        email = request.form['email']
        image = request.files['comp_image']
        print(image)
        select_query = "SELECT * FROM company"
        cursor.execute(select_query)
        # Fetch all rows of the result set
        result_set = cursor.fetchall()
        # Get the number of rows using the rowcount attribute of the cursor
        row_count = cursor.rowcount
        temp_comp_id = 'C' + str(1000 + row_count + 1)
        
        if image.filename == '':
            cursor = db_conn.cursor()
            add_comp_sql = "INSERT INTO company (comp_id,comp_name, comp_address, comp_phone, comp_background, comp_password, comp_email, comp_image) VALUES (%s, %s, %s,%s, %s, %s,%s, %s)"
            cursor.execute(add_comp_sql, (temp_comp_id, company_name, address, phone_number,background,password,email,image.filename))
            db_conn.commit()
        else:
            try:
                # Upload the report file to AWS S3
                emp_image_file_name_in_s3 = "comp-id-" + str(temp_comp_id) + "_company_logo.jpg"
                s3 = boto3.resource('s3')
                s3.Bucket(custombucket).put_object(Key=emp_image_file_name_in_s3, Body=image)
                bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
                s3_location = (bucket_location['LocationConstraint'])

                if s3_location is None:
                    s3_location = ''
                else:
                    s3_location = '-' + s3_location

                object_url = "https://{1}.s3.amazonaws.com/{2}".format(
                    s3_location,
                    custombucket,
                    emp_image_file_name_in_s3)
                cursor = db_conn.cursor()
                add_comp_sql = "INSERT INTO company (comp_id,comp_name, comp_address, comp_phone, comp_background, comp_password, comp_email, comp_image) VALUES (%s, %s, %s,%s, %s, %s,%s, %s)"
                cursor.execute(add_comp_sql, (temp_comp_id, company_name, address, phone_number,background,password,email, object_url))
                db_conn.commit()
            except Exception as e:
                return str(e)
        
        try:
            # Initialize lists to store job offers and allowances
            job_offers = []
            allowances = []

            # Loop through the form fields and check for non-empty values
            for i in range(1, 4):  # Adjust the range based on the number of fields
                job_offer_field = request.form.get(f"job_offer_{i}")
                allowance_field = request.form.get(f"allowance_{i}")

                # Check if the fields have values
                if job_offer_field and allowance_field:
                    job_offers.append(job_offer_field)
                    allowances.append(allowance_field)

            # Insert job offers and allowances into the database (you'll need to implement this part)
            # Example:
            count=1
            for job_offer, allowance in zip(job_offers, allowances):
                        
                select_query = "SELECT * FROM Job"
                cursor.execute(select_query)
                # Fetch all rows of the result set
                result_set = cursor.fetchall()
                # Get the number of rows using the rowcount attribute of the cursor
                row_count = cursor.rowcount
                temp_job_id = 'J' + str(1000 + row_count + 1)
                insert_job_offer_sql = "INSERT INTO Job (job_id, job_name, comp_id, allowance) VALUES (%s, %s, %s,%s)"
                cursor.execute(  insert_job_offer_sql, (temp_job_id, job_offer, temp_comp_id, allowance))
                db_conn.commit()
        except Exception as e:
            return str(e)
        # If authentication fails, you can display an error message
        success_message = "You have successfully added the company."
    return render_template('admin_add_company.html', success_message = success_message)


@app.route("/update_comp/<string:comp_id>", methods=['GET','POST'])
def update_comp(comp_id):
    success_message = None 
    cursor = db_conn.cursor()
    select_comp_sql = "SELECT * FROM company WHERE comp_id = %s"
    cursor.execute(select_comp_sql, (comp_id,))
    company = cursor.fetchone()

    select_job_sql = "SELECT * FROM Job WHERE comp_id = %s"
    cursor.execute(select_job_sql, (comp_id,))
    jobs = list(cursor.fetchall())
    max_jobs = 3
    for _ in range(len(jobs), max_jobs):
        jobs.append((" ", " "))  # Add empty values for missing jobs
    

    if request.method == 'POST':
        cursor = db_conn.cursor()
        company_name = request.form['company_name']
        phone_number = request.form['phone_number']
        address = request.form['address']
        background = request.form['background']
        password = request.form['password']
        email = request.form['email']
        comp_image = request.files['comp_image']
        if comp_image.filename == '':
            update_comp_sql = "UPDATE company SET comp_name=%s, comp_address=%s, comp_phone=%s, comp_background=%s, comp_password=%s, comp_email=%s WHERE comp_id = %s"
            cursor.execute(update_comp_sql, ( company_name, address, phone_number,background,password,email, comp_id))
            db_conn.commit()
        else:
            try:
                # Upload the report file to AWS S3
                emp_image_file_name_in_s3 = "comp-id-" + str(comp_id) + "_company_logo.jpg"
                s3 = boto3.resource('s3')
                s3.Bucket(custombucket).put_object(Key=emp_image_file_name_in_s3, Body=comp_image)
                bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
                s3_location = (bucket_location['LocationConstraint'])

                if s3_location is None:
                    s3_location = ''
                else:
                    s3_location = '-' + s3_location

                object_url = "https://{1}.s3.amazonaws.com/{2}".format(
                    s3_location,
                    custombucket,
                    emp_image_file_name_in_s3)
                update_comp_sql = "UPDATE company SET comp_name=%s, comp_address=%s, comp_phone=%s, comp_background=%s, comp_password=%s, comp_email=%s, comp_image=%s WHERE comp_id = %s"
                cursor.execute(update_comp_sql, ( company_name, address, phone_number,background,password,email, object_url, comp_id))
                db_conn.commit()
            except Exception as e:
                return str(e)
        try:

            # Initialize lists to store job offers and allowances
            job_offers = []
            allowances = []

            # Loop through the form fields and check for non-empty values
            for i in range(1, 4):  # Adjust the range based on the number of fields
                job_offer_field = request.form.get(f"job_offer_{i}")
                allowance_field = request.form.get(f"allowance_{i}")

                # Check if the fields have values
                if job_offer_field and allowance_field:
                    job_offers.append(job_offer_field)
                    allowances.append(allowance_field)

            # Insert job offers and allowances into the database (you'll need to implement this part)
            # Example:
            
                  
                cursor = db_conn.cursor()
                delete_job_sql = "DELETE FROM Job WHERE comp_id = %s"
                cursor.execute( delete_job_sql, (comp_id,))
                db_conn.commit()
            for job_offer, allowance in zip(job_offers, allowances):
                # Fetch all rows of the result set
                result_set = cursor.fetchall()
                # Get the number of rows using the rowcount attribute of the cursor
                cursor = db_conn.cursor()
                select_query = "SELECT * FROM Job"
                cursor.execute(select_query)
                row_count = cursor.rowcount
                temp_job_id = 'J' + str(1000 + row_count + 1)
                insert_job_offer_sql = "INSERT INTO Job (job_id, job_name, comp_id, allowance) VALUES (%s, %s, %s,%s)"
                cursor.execute(  insert_job_offer_sql, (temp_job_id, job_offer, comp_id, allowance))
                db_conn.commit()
        except Exception as e:
            return str(e)
        success_message = "You have successfully updated the company."
        select_comp_sql = "SELECT * FROM company WHERE comp_id = %s"
        cursor.execute(select_comp_sql, (comp_id,))
        company = cursor.fetchone()

        select_job_sql = "SELECT * FROM Job WHERE comp_id = %s"
        cursor.execute(select_job_sql, (comp_id,))
        jobs = list(cursor.fetchall())
        max_jobs = 3
        for _ in range(len(jobs), max_jobs):
            jobs.append((" ", " "))  # Add empty values for missing jobs
    return render_template('admin_update_company.html', company = company, success_message = success_message, jobs=jobs)

@app.route("/remove_comp/<string:comp_id>", methods=['GET','POST'])
def remove_comp(comp_id):
    success_message = None 
    try:
        cursor = db_conn.cursor()
        select_internship_sql = "SELECT * FROM internship WHERE comp_id = %s"
        cursor.execute(select_internship_sql, (comp_id,))
        internships = cursor.fetchall()  # Fetch all internships supervised by this supervisor

        # Use the comp_id to remove the company from the database
        for internship in internships:
            cursor = db_conn.cursor()
            update_internship_sql = "UPDATE internship SET comp_id = %s WHERE internship_id = %s"
            cursor.execute(update_internship_sql, (None, internship[0]))
            db_conn.commit()
    except Exception as e:
        return str(e)

    try:
        cursor = db_conn.cursor()
        delete_job_sql = "DELETE FROM Job WHERE comp_id = %s"
        cursor.execute( delete_job_sql, (comp_id,))

  
        # Define a SQL query to delete the company based on comp_id
        delete_company_sql = "DELETE FROM company WHERE comp_id = %s"
        cursor.execute(delete_company_sql, (comp_id,))
        
        # Commit the changes to the database
        db_conn.commit()
        success_message = "You have successfully removed the company."
        # Optionally, you can also delete related data from other tables if needed    
    except Exception as e:
        return str(e)
    
    cursor = db_conn.cursor()
    select_company_sql = "SELECT * FROM company"
    cursor.execute(select_company_sql)
    companies = cursor.fetchall()
    return render_template('admin.html', companies = companies, success_message=success_message)    
    
@app.route("/supervisor", methods=['GET'])
def supervisor():
    supervisor_id = request.args.get('supervisor_id')
    cursor = db_conn.cursor()

    select_super_sql = "SELECT * FROM supervisor WHERE super_id = %s"
    cursor.execute(select_super_sql, (supervisor_id,))
    supervisor = cursor.fetchone()

    select_internship_sql = "SELECT * FROM internship WHERE super_id = %s"
    cursor.execute(select_internship_sql, (supervisor_id,))
    internships = cursor.fetchall()  # Fetch all internships supervised by this supervisor
    
 
 # Initialize an empty list to store student details
    students = []

    # Loop through each internship to fetch student details
    for internship in internships:
        select_student_sql = "SELECT * FROM student WHERE stud_id = %s"
        cursor.execute(select_student_sql, (internship[1],))
        student = list(cursor.fetchone())  # Convert the student tuple into a list

        # Add the internship details to the student data
        student.append(internship[4])  # Job Position
        student.append(internship[5])  # Allowance
        student.append(internship[7])  # Grade
        student.append(internship[8])  # Status
        students.append(student)  # Append student data to the list
       
    return render_template('supervisor.html', supervisor=supervisor, students=students)

@app.route("/supervisor/<string:stud_id>", methods=['GET','POST'])
def supervisor_student(supervisor,stud_id):
    cursor = db_conn.cursor()
    
    # Retrieve student details based on the stud_id
    select_student_sql = "SELECT * FROM student WHERE stud_id = %s"
    cursor.execute(select_student_sql, (stud_id,))
    student = cursor.fetchone() # Convert the student tuple into a dictionary

    select_internship_sql = "SELECT * FROM internship WHERE stud_id = %s"
    cursor.execute(select_internship_sql, (stud_id,))
    internship =cursor.fetchone() # Fetch all internships supervised by this supervisor
    print(internship)

    select_company_sql = "SELECT * FROM company WHERE comp_id = %s"
    cursor.execute(select_company_sql, (internship[2],))
    company = cursor.fetchone()  # Fetch company details of that student for interns
    print(company)

    select_supervisor_sql = "SELECT * FROM supervisor WHERE super_id = %s"
    cursor.execute(select_supervisor_sql, (internship[3],))
    supervisor = cursor.fetchone()  # Fetch all internships supervised by this supervisor

    if request.method == 'POST':
        report = request.files['file']
        report_id = request.form['report_id']
        if report.filename == '':
            return "Please select a file"

        try:
            # Upload the report file to AWS S3
            emp_report_file_name_in_s3 = "report-id-" + str(report_id) + "_report_file.pdf"
            s3 = boto3.resource('s3')
            s3.Bucket(custombucket).put_object(Key=emp_report_file_name_in_s3, Body=report)
            bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
            s3_location = (bucket_location['LocationConstraint'])

            if s3_location is None:
                s3_location = ''
            else:
                s3_location = '-' + s3_location

            object_url = "https://{1}.s3.amazonaws.com/{2}".format(
                s3_location,
                custombucket,
                emp_report_file_name_in_s3)
            
            print(object_url)
            # Get the current date in the "YYYY-MM-DD" format
            current_date = datetime.now().strftime('%Y-%m-%d')

            # Update the report with the object URL and current date
            cursor = db_conn.cursor()
            update_report_sql = "UPDATE report SET report_file=%s, report_date_submit=%s WHERE stud_id = %s AND report_id = %s"
            cursor.execute(update_report_sql, (object_url, current_date, stud_id, report_id))
            db_conn.commit()

        except Exception as e:
            return str(e)

    select_report_sql = "SELECT * FROM report WHERE stud_id = %s"
    cursor.execute(select_report_sql, (stud_id,))
    reports = cursor.fetchall()  # Fetch all internships supervised by this supervisor
    print(reports)
    return render_template('supervisor_student.html', student=student, internship=internship, supervisor=supervisor, company=company, reports=reports)




@app.route("/student_evaluation/<string:stud_id>", methods=['GET', 'POST'])
def student_evaluation(stud_id):
    success_message = None  # Initialize the success_message variable
    cursor = db_conn.cursor()

    if request.method == 'GET':
        # Retrieve student details based on the stud_id
        select_student_sql = "SELECT * FROM student WHERE stud_id = %s"
        cursor.execute(select_student_sql, (stud_id,))
        student = list(cursor.fetchone())  # Convert the student tuple into a list

        select_evaluation_sql = "SELECT * FROM evaluation WHERE stud_id = %s"
        cursor.execute(select_evaluation_sql, (stud_id,))
        evaluation = list(cursor.fetchone())  # Convert the student tuple into a list

        select_internship_sql = "SELECT * FROM internship WHERE stud_id = %s"
        cursor.execute(select_internship_sql, (stud_id,))
        internship = list(cursor.fetchone())  # Convert the student tuple into a list

        if evaluation[2] == 0 or evaluation[3] == 0 or evaluation[4] == 0:
            evaluation[2] = ""
            evaluation[3] = ""
            evaluation[4] = ""
            total_marks = ""
        else:
            total_marks = evaluation[2] + evaluation[3] + evaluation[4]
            evaluation.append(total_marks)

    if request.method == 'POST':
        stage1 = int(request.form['stage1'])
        stage2 = int(request.form['stage2'])
        stage3 = int(request.form['stage3'])
        feedback = request.form['feedback']

        # Update the evaluation data in the database
        update_eva_sql = "UPDATE evaluation SET stage1 = %s, stage2 = %s, stage3 = %s, feedback = %s WHERE stud_id = %s"
        cursor.execute(update_eva_sql, (stage1, stage2, stage3, feedback, stud_id))

        total_marks = stage1 + stage2  + stage3
        print(total_marks)
        if total_marks >=250:
            grade = "A"
        elif total_marks >= 200:
            grade = "B"
        elif total_marks >= 150:
            grade = "C"
        elif total_marks >= 100:
            grade = "D"
        elif total_marks >= 50:
            grade = "E"
        else:
            grade = "F" 
        
        print(grade)
        update_grade_sql = "UPDATE internship SET grade=%s WHERE stud_id = %s"
        cursor.execute(update_grade_sql, (grade, stud_id))
        db_conn.commit()

        # If authentication fails, you can display an error message
        success_message = "You have successfully evaluated the student."

    # Retrieve student details (again) in case they were updated
    select_student_sql = "SELECT * FROM student WHERE stud_id = %s"
    cursor.execute(select_student_sql, (stud_id,))
    student = list(cursor.fetchone())  # Convert the student tuple into a list

    select_evaluation_sql = "SELECT * FROM evaluation WHERE stud_id = %s"
    cursor.execute(select_evaluation_sql, (stud_id,))
    evaluation = cursor.fetchone() # Convert the student tuple into a list

    select_internship_sql = "SELECT * FROM internship WHERE stud_id = %s"
    cursor.execute(select_internship_sql, (stud_id,))
    internship = list(cursor.fetchone())  # Convert the student tuple into a list

    return render_template('student_evaluation.html', student=student, evaluation=evaluation, internship=internship, success_message=success_message)



@app.route("/student", methods=['GET','POST'])
def student():
    stud_id = request.args.get('student_id')
    cursor = db_conn.cursor()
    # Retrieve student details based on the stud_id
    select_student_sql = "SELECT * FROM student WHERE stud_id = %s"
    cursor.execute(select_student_sql, (stud_id,))
    student = cursor.fetchone() # Convert the student tuple into a dictionary

    select_internship_sql = "SELECT * FROM internship WHERE stud_id = %s"
    cursor.execute(select_internship_sql, (stud_id,))
    internship =cursor.fetchone() # Fetch all internships supervised by this supervisor
    print(internship)

    # Check if there is no internship record for the student
    if internship[2] is None:
        # Redirect the student to the student_addcomp function
        return redirect(url_for('student_addcomp'))

    select_company_sql = "SELECT * FROM company WHERE comp_id = %s"
    cursor.execute(select_company_sql, (internship[2],))
    company = cursor.fetchone()  # Fetch company details of that student for interns
    print(company)

    select_supervisor_sql = "SELECT * FROM supervisor WHERE super_id = %s"
    cursor.execute(select_supervisor_sql, (internship[3],))
    supervisor = cursor.fetchone()  # Fetch all internships supervised by this supervisor

    if request.method == 'POST':
        report = request.files['file']
        report_id = request.form['report_id']
        if report.filename == '':
            return "Please select a file"

        try:
            # Upload the report file to AWS S3
            emp_report_file_name_in_s3 = "report-id-" + str(report_id) + "_report_file.pdf"
            s3 = boto3.resource('s3')
            s3.Bucket(custombucket).put_object(Key=emp_report_file_name_in_s3, Body=report)
            bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
            s3_location = (bucket_location['LocationConstraint'])

            if s3_location is None:
                s3_location = ''
            else:
                s3_location = '-' + s3_location

            object_url = "https://{1}.s3.amazonaws.com/{2}".format(
                s3_location,
                custombucket,
                emp_report_file_name_in_s3)
            
            print(object_url)
            # Get the current date in the "YYYY-MM-DD" format
            current_date = datetime.now().strftime('%Y-%m-%d')

            # Update the report with the object URL and current date
            cursor = db_conn.cursor()
            update_report_sql = "UPDATE report SET report_file=%s, report_date_submit=%s WHERE stud_id = %s AND report_id = %s"
            cursor.execute(update_report_sql, (object_url, current_date, stud_id, report_id))
            db_conn.commit()

        except Exception as e:
            return str(e)

    select_report_sql = "SELECT * FROM report WHERE stud_id = %s"
    cursor.execute(select_report_sql, (stud_id,))
    reports = cursor.fetchall()  # Fetch all internships supervised by this supervisor
    print(reports)
    return render_template('student_details.html', student=student, internship=internship, supervisor=supervisor, company=company, reports=reports)

@app.route("/student_addcomp", methods=['GET','POST'])
def student_addcomp():
    stud_id = session["user_id"]
    cursor = db_conn.cursor()
    # Retrieve student details based on the stud_id
    select_student_sql = "SELECT * FROM student WHERE stud_id = %s"
    cursor.execute(select_student_sql, (stud_id,))
    student = cursor.fetchone() # Convert the student tuple into a dictionary

    select_internship_sql = "SELECT * FROM internship WHERE stud_id = %s"
    cursor.execute(select_internship_sql, (stud_id,))
    internship =cursor.fetchone() # Fetch all internships supervised by this supervisor
 
    select_supervisor_sql = "SELECT * FROM supervisor WHERE super_id = %s"
    cursor.execute(select_supervisor_sql, (internship[3],))
    supervisor = cursor.fetchone()  # Fetch all internships supervised by this supervisor
    
    select_company_sql = "SELECT * FROM company"
    cursor.execute(select_company_sql)
    companies = cursor.fetchall()

    if request.method == 'POST':
        report = request.files['file']
        report_id = request.form['report_id']
        if report.filename == '':
            return "Please select a file"

        try:
            # Upload the report file to AWS S3
            emp_report_file_name_in_s3 = "report-id-" + str(report_id) + "_report_file.pdf"
            s3 = boto3.resource('s3')
            s3.Bucket(custombucket).put_object(Key=emp_report_file_name_in_s3, Body=report)
            bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
            s3_location = (bucket_location['LocationConstraint'])

            if s3_location is None:
                s3_location = ''
            else:
                s3_location = '-' + s3_location

            object_url = "https://{1}.s3.amazonaws.com/{2}".format(
                s3_location,
                custombucket,
                emp_report_file_name_in_s3)
            
            print(object_url)
            # Get the current date in the "YYYY-MM-DD" format
            current_date = datetime.now().strftime('%Y-%m-%d')

            # Update the report with the object URL and current date
            cursor = db_conn.cursor()
            update_report_sql = "UPDATE report SET report_file=%s, report_date_submit=%s WHERE stud_id = %s AND report_id = %s"
            cursor.execute(update_report_sql, (object_url, current_date, stud_id, report_id))
            db_conn.commit()

        except Exception as e:
            return str(e)

    select_report_sql = "SELECT * FROM report WHERE stud_id = %s"
    cursor.execute(select_report_sql, (stud_id,))
    reports = cursor.fetchall()  # Fetch all internships supervised by this supervisor
    print(reports)
    return render_template('student_add_company.html', student=student, internship=internship, supervisor=supervisor, companies=companies, reports=reports)

@app.route("/add_intern_details", methods=["POST"])
def add_intern_details():
     if request.method == 'POST':
        # Get form data
        company_name = request.form.get('company')
        cursor = db_conn.cursor()
        selected_company_id_sql = "SELECT* FROM company WHERE comp_name = %s"
        cursor.execute(selected_company_id_sql, (company_name,))
        selected_company_id = cursor.fetchone()

        stud_id = session["user_id"]
        select_internship_sql = "SELECT * FROM internship WHERE stud_id = %s"
        cursor.execute(select_internship_sql, (stud_id,))
        internship =cursor.fetchone() # Fetch all internships supervised by this supervisor
        print(internship)

        internship_id = internship[0]
        job_position = request.form.get('job_position')

        cursor = db_conn.cursor()
        select_job_sql = "SELECT * FROM Job WHERE job_id = %s"
        cursor.execute( select_job_sql, (job_position,))
        job=cursor.fetchone()

        job_duration = int(request.form.get('job_duration'))
        job_allowance = int(request.form.get('job_allowance'))

        print(internship_id, job_position, job_duration, job_allowance )
         # Update the report with the object URL and current date
        cursor = db_conn.cursor()
        update_internship_sql = "UPDATE internship SET comp_id=%s, job_position=%s, allowance=%s,  duration=%s WHERE internship_id = %s"
        cursor.execute(update_internship_sql, ( selected_company_id[0],  job[1], job_allowance,  job_duration, internship_id))
        db_conn.commit()

        stud_id = session["user_id"]
        cursor = db_conn.cursor()
        # Retrieve student details based on the stud_id
        select_student_sql = "SELECT * FROM student WHERE stud_id = %s"
        cursor.execute(select_student_sql, (stud_id,))
        student = cursor.fetchone() # Convert the student tuple into a dictionary

        select_internship_sql = "SELECT * FROM internship WHERE stud_id = %s"
        cursor.execute(select_internship_sql, (stud_id,))
        internship =cursor.fetchone() # Fetch all internships supervised by this supervisor
        print(internship)

        select_company_sql = "SELECT * FROM company WHERE comp_id = %s"
        cursor.execute(select_company_sql, (internship[2],))
        company = cursor.fetchone()  # Fetch company details of that student for interns
        print(company)

        select_supervisor_sql = "SELECT * FROM supervisor WHERE super_id = %s"
        cursor.execute(select_supervisor_sql, (internship[3],))
        supervisor = cursor.fetchone()  # Fetch all internships supervised by this supervisor
        select_report_sql = "SELECT * FROM report WHERE stud_id = %s"
        cursor.execute(select_report_sql, (stud_id,))
        reports = cursor.fetchall()  # Fetch all internships supervised by this supervisor
        print(reports)
        
        return render_template('student_details.html', student=student, internship=internship, supervisor=supervisor, company=company, reports=reports)


@app.route("/get_job_positions", methods=["POST"])
def get_job_positions():
    # Get the selected company ID from the AJAX request data
    selected_company_name = request.form.get("company_id")
    cursor = db_conn.cursor()
    selected_company_id_sql = "SELECT* FROM company WHERE comp_name = %s"
    cursor.execute(selected_company_id_sql, (selected_company_name,))
    selected_company_id = cursor.fetchone()

    # Fetch job positions based on the selected company ID
    cursor = db_conn.cursor()
    select_job_positions_sql = "SELECT job_id, job_name FROM Job WHERE comp_id = %s"
    cursor.execute(select_job_positions_sql, (selected_company_id[0],))
    job_positions = cursor.fetchall()

    # Create a list of dictionaries containing job position information
    job_positions_list = [{"id": position[0], "name": position[1]} for position in job_positions]
    print(job_positions_list)
    # Return the job positions as JSON
    return jsonify({"job_positions": job_positions_list})

@app.route("/get_allowance", methods=["POST"])
def get_allowance():
    # Get the selected job position ID from the AJAX request data
    selected_job_position_id = request.form.get("job_position_id")
    cursor = db_conn.cursor()
    select_allowance_sql = "SELECT allowance FROM Job WHERE job_id = %s"
    cursor.execute(select_allowance_sql, (selected_job_position_id,))
    allowance = cursor.fetchone()[0]

    # Return the allowance as JSON
    return jsonify({"allowance": allowance})

@app.route("/login", methods=['GET', 'POST'])
def login():
    error_message = None  # Initialize the error_message variable

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Use a cursor to interact with the database
        cursor = db_conn.cursor()

        # Define the SQL queries to retrieve user data based on the provided email
        admin_select_sql = "SELECT * FROM admin WHERE admin_email = %s"
        supervisor_select_sql = "SELECT * FROM supervisor WHERE super_email = %s"
        student_select_sql = "SELECT * FROM student WHERE stud_email = %s"
        company_select_sql = "SELECT * FROM company WHERE comp_email = %s"

        # Execute the queries with the provided email
        cursor.execute(admin_select_sql, (email,))
        admin = cursor.fetchone()  # Fetch admin data

        cursor.execute(supervisor_select_sql, (email,))
        supervisor = cursor.fetchone()  # Fetch supervisor data

        cursor.execute(student_select_sql, (email,))
        student = cursor.fetchone()  # Fetch student data

        cursor.execute(company_select_sql, (email,))
        company = cursor.fetchone()  # Fetch student data

        if admin is not None and admin[2] == password:
            # Authentication successful for admin
            # Store user information in the session (optional)
        
            return redirect(url_for('admin',admin_id = admin[0]))

        elif supervisor is not None and supervisor[9] == password:
            # Authentication successful for supervisor
            # Store user information in the session (optional)
            return redirect(url_for('supervisor',supervisor_id = supervisor[0]))

        elif student is not None and student[8] == password:
            # Authentication successful for student
            # Store user information in the session (optional)
    
            return redirect(url_for('student', student_id = student[0]))
        
        elif company is not None and company[6] == password:
            # Authentication successful for student
            # Store user information in the session (optional)
          
            return redirect(url_for('company', company_id = company[0]))

        # If authentication fails, you can display an error message
        error_message = "Invalid email or password. Please try again."

    # If the request method is GET or authentication fails, render the login template
    return render_template('login.html', error_message=error_message)



@app.route("/addemp", methods=['POST'])
def AddEmp():
    emp_id = request.form['emp_id']
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    pri_skill = request.form['pri_skill']
    location = request.form['location']
    emp_image_file = request.files['emp_image_file']

    insert_sql = "INSERT INTO employee VALUES (%s, %s, %s, %s, %s)"
    cursor = db_conn.cursor()

    if emp_image_file.filename == "":
        return "Please select a file"

    try:

        cursor.execute(insert_sql, (emp_id, first_name, last_name, pri_skill, location))
        db_conn.commit()
        emp_name = "" + first_name + " " + last_name
        # Uplaod image file in S3 #
        emp_image_file_name_in_s3 = "emp-id-" + str(emp_id) + "_image_file"
        s3 = boto3.resource('s3')

        try:
            print("Data inserted in MySQL RDS... uploading image to S3...")
            s3.Bucket(custombucket).put_object(Key=emp_image_file_name_in_s3, Body=emp_image_file)
            bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
            s3_location = (bucket_location['LocationConstraint'])

            if s3_location is None:
                s3_location = ''
            else:
                s3_location = '-' + s3_location

            object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                s3_location,
                custombucket,
                emp_image_file_name_in_s3)

        except Exception as e:
            return str(e)

    finally:
        cursor.close()

    print("all modification done...")
    return render_template('index.html', name=emp_name)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)

