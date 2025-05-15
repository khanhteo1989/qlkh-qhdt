from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
import pandas as pd
import random
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload

# Phạm vi quyền truy cập Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def authenticate_google_account():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=5000)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return build('drive', 'v3', credentials=creds)

def save_form_data_to_drive(form_data):
    service = authenticate_google_account()
    file_name = f"{form_data['name']}_form_data.txt"
    file_metadata = {'name': file_name, 'mimeType': 'text/plain'}
    with open(file_name, 'w') as f:
        f.write(str(form_data))
    media = MediaFileUpload(file_name, mimetype='text/plain')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    print(f"File ID: {file['id']}")
    os.remove(file_name)

CV_CODES = [
    "CV01 - KHÁNH", "CV02 - X.Thủy", "CV03 - Ngọc Anh", "CV04 - Nhật Linh",
    "CV05 - Hoàng Biên", "CV06 - Hải", "CV07 - Hoàng Trang", "CV08 - Ly",
    "CV09 - Tiến Cường", "CV010 - Hoàng Thân", "CV011 - Trang(Teamlinh)", 
    "CV12 - Quảng Ninh1", "CV013 - Quảng Ninh2"
]

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///customers.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'xls', 'xlsx'}

db = SQLAlchemy(app)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    cccd = db.Column(db.String(20), nullable=False)
    dob = db.Column(db.String(20), nullable=False)
    role = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(100), nullable=False)
    program = db.Column(db.String(100), nullable=False)
    notes = db.Column(db.String(200), nullable=True)
    date_added = db.Column(db.DateTime, nullable=False, default=pd.to_datetime("now"))
    treatment_plans = db.Column(db.String(500), nullable=True)
    appointment_schedules = db.Column(db.String(500), nullable=True)
    revenues = db.Column(db.String(500), nullable=True)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    customers = Customer.query.paginate(page=page, per_page=20, error_out=False)
    return render_template('index.html', customers=customers, cv_codes=CV_CODES)

def generate_cccd():
    return "DN-" + str(random.randint(1000000000, 9999999999))

@app.route('/add_customer', methods=['POST'])
def add_customer():
    form_data = {
        'name': request.form['name'],
        'phone': request.form['phone'],
        'address': request.form['address'],
        'dob': request.form['dob'],
        'cccd': request.form['cccd'],
        'role': request.form['cv_code'],
        'status': request.form['status'],
        'program': request.form['program'],
        'notes': request.form['notes']
    }
    save_form_data_to_drive(form_data)

    new_customer = Customer(
        name=form_data['name'],
        address=form_data['address'],
        phone=form_data['phone'],
        cccd=form_data['cccd'],
        dob=form_data['dob'],
        role=form_data['role'],
        status=form_data['status'],
        program=form_data['program'],
        notes=form_data['notes']
    )
    db.session.add(new_customer)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/edit_customer/<int:customer_id>', methods=['GET', 'POST'])
def edit_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    treatment_plans = customer.treatment_plans.split(',') if customer.treatment_plans else []
    appointment_schedules = customer.appointment_schedules.split(',') if customer.appointment_schedules else []
    revenues = customer.revenues.split(',') if customer.revenues else []

    if request.method == 'POST':
        customer.name = request.form['name']
        customer.address = request.form['address']
        customer.phone = request.form['phone']
        customer.cccd = request.form['cccd']
        customer.dob = request.form['dob']
        customer.role = request.form['role']
        customer.status = request.form['status']
        customer.program = request.form['program']
        customer.notes = request.form['notes']

        customer.treatment_plans = ",".join(request.form.getlist('treatment_plan'))
        customer.appointment_schedules = ",".join(request.form.getlist('appointment_schedule'))
        customer.revenues = ",".join(request.form.getlist('revenue'))

        form_data = {
            'name': customer.name,
            'phone': customer.phone,
            'address': customer.address,
            'dob': customer.dob,
            'cccd': customer.cccd,
            'role': customer.role,
            'status': customer.status,
            'program': customer.program,
            'notes': customer.notes
        }
        save_form_data_to_drive(form_data)

        db.session.commit()
        return redirect(url_for('index'))

    return render_template('edit_customer.html', customer=customer,
                           treatment_plans=treatment_plans,
                           appointment_schedules=appointment_schedules,
                           revenues=revenues)

@app.route('/customer/<int:customer_id>')
def view_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    treatment_plans = customer.treatment_plans.split(',') if customer.treatment_plans else []
    appointment_schedules = customer.appointment_schedules.split(',') if customer.appointment_schedules else []
    revenues = customer.revenues.split(',') if customer.revenues else []
    return render_template('customer_detail.html', customer=customer,
                           treatment_plans=treatment_plans,
                           appointment_schedules=appointment_schedules,
                           revenues=revenues)

@app.route('/delete_customer/<int:customer_id>')
def delete_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    db.session.delete(customer)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    if request.method == 'POST':
        if 'file' not in request.files:
            return 'No file part'
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            df = pd.read_excel(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            for index, row in df.iterrows():
                customer = Customer(
                    name=row['Họ Tên'],
                    address=row['Địa Chỉ'],
                    phone=row['SĐT'],
                    cccd=row['Mã nv,CCCD'],
                    dob=row['Ngày Sinh'],
                    role=row['CV Quản Lý'],
                    status=row['Tình Trạng'],
                    program=row['CT Áp Dụng'] if 'CT Áp Dụng' in df.columns else 'Chưa có thông tin',
                    notes=row['Ghi Chú'],
                    treatment_plans=row['Lộ Trình Chữa Bệnh'],
                    appointment_schedules=row['Lịch Hẹn'],
                    revenues=row['Doanh Thu']
                )
                db.session.add(customer)
            db.session.commit()
            customers = Customer.query.all()
            return render_template('upload.html', customers=customers)

    return render_template('upload.html')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

if __name__ == '__main__':
    app.run(debug=True)
