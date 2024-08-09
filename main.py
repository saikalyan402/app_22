from flask import Flask, redirect, url_for, render_template, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'

db = SQLAlchemy(app)

# Models
class Brand(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    is_flagged = db.Column(db.Boolean, default=False)
#    campaigns = db.relationship('Campaign', backref='sponsor', lazy=True)

class Influencer(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    is_flagged = db.Column(db.Boolean, default=False)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    roles = db.relationship('Role', secondary='user_role', backref=db.backref('user', lazy='dynamic'))
    Brand = db.relationship('Brand', backref='user', uselist=False)
    Influencer = db.relationship('Influencer', backref='user', uselist=False)

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    role_name = db.Column(db.String(255), nullable=False)

class UserRole(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))

class Campaign(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    niche = db.Column(db.String(255), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    budget = db.Column(db.Float, nullable=False)
    is_private = db.Column(db.Boolean, nullable=False)
    brand_id = db.Column(db.Integer, db.ForeignKey('brand.id'), nullable=False)
    brand = db.relationship('Brand', backref=db.backref('campaigns', lazy=True))
    desc = db.Column(db.String(1000), nullable=True)
    requirement = db.Column(db.String(1000), nullable=True)
    ad_requests = db.relationship('AdRequest', backref='campaign', lazy=True)



class AdRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    influencer_id = db.Column(db.Integer, nullable=False)  # Make sure this column exists
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    payment_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(255), default='pending')  # pending, accepted, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)



# Routes
@app.route('/')
def hello_world():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id  # Store user ID in the session
            
            # Ensure the user has roles before accessing them
            if not user.roles:
                flash('No role assigned to this user. Please contact support.', 'error')
                return redirect(url_for('login'))
            
            # Determine the user's role and redirect accordingly
            role = user.roles[0].role_name  # Assuming one role per user
            if role == 'Influencer':
                return redirect(url_for('influencer_home'))
            elif role == 'Brand':
                return redirect(url_for('brand_home'))
            elif role == 'Admin':
                return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password')
            return redirect(url_for('login'))
    return render_template('login.html')


@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/register/<role>', methods=['GET', 'POST'])
def register_role(role):
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))

        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        # Create Brand if role is Brand
        if role.lower() == 'brand':
            brand_name = request.form['brand_name']  # Add a field for the brand name
            brand = Brand(name=brand_name, user_id=new_user.id)
            db.session.add(brand)
            db.session.commit()

        assigned_role = Role.query.filter_by(role_name=role.capitalize()).first()
        if assigned_role:
            user_role = UserRole(user_id=new_user.id, role_id=assigned_role.id)
            db.session.add(user_role)
            db.session.commit()

        flash(f'Registration successful as {role.capitalize()}! Please log in.')
        if role.lower() == 'influencer':
            return redirect(url_for('influencer_home'))
        elif role.lower() == 'brand':
            return redirect(url_for('brand_home'))
        elif role.lower() == 'admin':
            return redirect(url_for('admin_dashboard'))
    return render_template('register_role.html', role=role)

@app.route('/influencer_home')
def influencer_home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('influencer.html')

@app.route('/brand_home')
def brand_home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session.get('user_id')
    print(f"User ID from session: {user_id}")
    
    user = db.session.get(User, user_id)
    if not user:
        flash('Unauthorized access.')
        return redirect(url_for('login'))

    brand = Brand.query.filter_by(user_id=user.id).first()
    if not brand:
        flash('Unauthorized access.')
        return redirect(url_for('login'))

    campaigns = Campaign.query.filter_by(brand_id=brand.id).all()
    
    if not campaigns:
        print("No campaigns found for this brand.")
    else:
        for campaign in campaigns:
            print(f"Found campaign: {campaign.name}")

    return render_template('brand_main.html', campaigns=campaigns)


@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    active_users = User.query.count()
    public_campaigns = Campaign.query.filter_by(is_private=False).count()
    private_campaigns = Campaign.query.filter_by(is_private=True).count()
    ad_requests = AdRequest.query.all()  # Change this line to get all ad requests, not just the count
    flagged_brands = Brand.query.filter_by(is_flagged=True).count()
    flagged_influencers = Influencer.query.filter_by(is_flagged=True).count()

    return render_template('admin_dashboard.html', 
                           active_users=active_users,
                           public_campaigns=public_campaigns,
                           private_campaigns=private_campaigns,
                           ad_requests=ad_requests,  # Pass the list of ad requests
                           flagged_sponsors=flagged_brands,
                           flagged_influencers=flagged_influencers)

@app.route('/campaigns', methods=['GET'])
def campaigns():
    if 'user_id' not in session:
        print("No user_id in session")
        return redirect(url_for('login'))
    
    user_id = session.get('user_id')
    print(f"User ID from session: {user_id}")

    user = db.session.get(User, user_id)
    if not user:
        print("User not found")
        flash('Unauthorized access.')
        return redirect(url_for('login'))

    brand = Brand.query.filter_by(user_id=user.id).first()
    if not brand:
        flash('Unauthorized access.')
        return redirect(url_for('login'))

    campaigns = Campaign.query.filter_by(brand_id=brand.id).all()
    return render_template('campaigns.html', campaigns=campaigns)

@app.route('/campaigns/new', methods=['GET', 'POST'])
def new_campaign():
    # if 'user_id' not in session:
    #     return redirect(url_for('login'))

    user_id = session.get('user_id')
    user = User.query.get(user_id)
    # if not user:
    #     flash('Unauthorized access.')
    #     return redirect(url_for('login'))

    # # Check if user is a Brand
    brand = Brand.query.filter_by(user_id=user.id).first()
    # if not brand:
    #     flash('Unauthorized access.')
    #     return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        niche = request.form['niche']
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d')
        budget = float(request.form['budget'])
        is_private = 'is_private' in request.form  # Checkbox
        desc = request.form.get('desc')  # Get the description from the form
        requirement = request.form.get('requirement') 


        new_campaign = Campaign(
            name=name,
            niche=niche,
            start_date=start_date,
            end_date=end_date,
            budget=budget,
            is_private=is_private,
            brand_id=brand.id,
            desc=desc,  # Save the description
            requirement=requirement  # Save the requirement 
        )

        db.session.add(new_campaign)
        db.session.commit()
        flash('Campaign created successfully!')

        return redirect(url_for('brand_home'))

    return render_template('new_campaign.html')

@app.route('/campaigns/update/<int:campaign_id>', methods=['GET', 'POST'])
def update_campaign(campaign_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)
    if not user:
        flash('Unauthorized access.')
        return redirect(url_for('login'))

    brand = Brand.query.filter_by(user_id=user.id).first()
    if not brand:
        flash('Unauthorized access.')
        return redirect(url_for('login'))

    campaign = Campaign.query.get_or_404(campaign_id)

    if request.method == 'POST':
        campaign.name = request.form['name']
        campaign.niche = request.form['niche']
        campaign.start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
        campaign.end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d')
        campaign.budget = float(request.form['budget'])
        campaign.is_private = 'is_private' in request.form
        campaign.desc = request.form.get('desc')  # Update the description
        campaign.requirement = request.form.get('requirement')  # Update the requirement    

        db.session.commit()
        flash('Campaign updated successfully!')
        return redirect(url_for('campaigns'))

    return render_template('update_campaign.html', campaign=campaign)


@app.route('/campaigns/delete/<int:campaign_id>', methods=['POST'])
def delete_campaign(campaign_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)
    if not user:
        flash('Unauthorized access.')
        return redirect(url_for('login'))

    brand = Brand.query.filter_by(user_id=user.id).first()
    if not brand:
        flash('Unauthorized access.')
        return redirect(url_for('login'))

    campaign = Campaign.query.get_or_404(campaign_id)

    db.session.delete(campaign)
    db.session.commit()
    flash('Campaign deleted successfully!')
    return redirect(url_for('campaigns'))

@app.route('/ad_requests')
def view_ad_requests():
    ad_requests = AdRequest.query.all()
    return render_template('view_ad_requests.html', ad_requests=ad_requests)

@app.route('/ad_request/<int:ad_request_id>/accept', methods=['POST'])
def accept_ad_request(ad_request_id):
    ad_request = AdRequest.query.get_or_404(ad_request_id)
    ad_request.status = 'accepted'
    db.session.commit()
    flash('Ad request accepted successfully!')
    return redirect(url_for('view_ad_requests'))

@app.route('/ad_request/<int:ad_request_id>/reject', methods=['POST'])
def reject_ad_request(ad_request_id):
    ad_request = AdRequest.query.get_or_404(ad_request_id)
    ad_request.status = 'rejected'
    db.session.commit()
    flash('Ad request rejected successfully!')
    return redirect(url_for('view_ad_requests'))

@app.route('/ad_request/<int:ad_request_id>/negotiate', methods=['GET', 'POST'])
def negotiate_ad_request(ad_request_id):
    ad_request = AdRequest.query.get_or_404(ad_request_id)
    if request.method == 'POST':
        new_amount = float(request.form['payment_amount'])
        ad_request.payment_amount = new_amount
        db.session.commit()
        flash('Ad request payment amount negotiated successfully!')
        return redirect(url_for('view_ad_requests'))
    return render_template('negotiate_ad_request.html', ad_request=ad_request)



@app.route('/logout')
def logout():
    session.pop('user_id', None)  # Remove user ID from session
    flash('You have been logged out.')
    return redirect(url_for('login'))

def create_db():
    with app.app_context():
        db.create_all()

        # Create roles if they don't exist
        if not Role.query.filter_by(role_name='Brand').first():
            db.session.add(Role(role_name='Brand'))
        if not Role.query.filter_by(role_name='Influencer').first():
            db.session.add(Role(role_name='Influencer'))
        if not Role.query.filter_by(role_name='Admin').first():
            db.session.add(Role(role_name='Admin'))

        # Add test admin user
        if not User.query.filter_by(username='Admin').first():
            new_user = User(
                username='Admin',
                email='admin@email.com',
                password=generate_password_hash('testpassword')
            )
            db.session.add(new_user)
            db.session.commit()

            # Assign the 'Admin' role to the user
            role = Role.query.filter_by(role_name='Admin').first()
            if role:
                user_role = UserRole(user_id=new_user.id, role_id=role.id)
                db.session.add(user_role)
                db.session.commit()

        db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        create_db()  # Call the function to create tables and populate initial data
    app.run(debug=True)

