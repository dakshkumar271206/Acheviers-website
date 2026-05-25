from flask import Flask, render_template_string, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "achievers_secret_key_2024"

# --- DATABASE CONFIGURATION ---
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'achievers.db')
app.config['SQLALCHEMY_BINDS'] = {
    'users': 'sqlite:///' + os.path.join(basedir, 'users.db')
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MODELS ---
class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    father_name = db.Column(db.String(100), nullable=False)
    course = db.Column(db.String(100), nullable=False) # Maps to "Class"
    contact = db.Column(db.String(20), nullable=False)
    date_submitted = db.Column(db.DateTime, default=datetime.utcnow)

class User(db.Model):
    __bind_key__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False) # 'admin', 'teacher', 'student'
    is_verified = db.Column(db.Boolean, default=False)

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        db.session.add_all([
            User(username='admin', password='admin123', email='admin@achievers.com', role='admin', is_verified=True),
            User(username='teacher', password='teacher123', email='teacher@achievers.com', role='teacher', is_verified=True),
            User(username='student', password='student123', email='student@achievers.com', role='student', is_verified=True)
        ])
        db.session.commit()

# --- SHARED HTML COMPONENTS ---
BASE_HEAD = """
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Achievers | {{ title }}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&family=Playfair+Display:ital,wght@0,700;1,700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; scroll-behavior: smooth; background-color: #001f3f; color: #f8fafc; }
        .font-serif { font-family: 'Playfair Display', serif; }
        .btn-animate { transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); cursor: pointer; }
        @keyframes zoomIn { from { opacity: 0; transform: scale(0.95); } to { opacity: 1; transform: scale(1); } }
        .animate-zoom-in { animation: zoomIn 0.3s ease-out forwards; }
        .nav-link { position: relative; }
        .nav-link::after { content: ''; position: absolute; bottom: -4px; left: 0; width: 0; height: 2px; background: #ef4444; transition: width 0.3s; }
        .nav-link:hover::after { width: 100%; }
        .active-link::after { width: 100%; }
        .role-tab { transition: all 0.3s ease; border: 1px solid transparent; }
        .role-tab.active { background: #dc2626; color: white; border-color: #dc2626; }
    </style>
</head>
"""

NAVBAR = """
<nav id="navbar" class="fixed w-full z-50 transition-all py-6 bg-blue-950/95 backdrop-blur-md border-b border-white/10">
    <div class="max-w-7xl mx-auto px-6 flex justify-between items-center">
        <a href="/" class="flex items-center space-x-2 group">
            <div class="w-10 h-10 bg-red-600 rounded-xl flex items-center justify-center shadow-lg group-hover:rotate-12 transition-transform">
                <i data-lucide="graduation-cap" class="text-white w-6 h-6"></i>
            </div>
            <div class="flex flex-col">
                <span class="text-xl font-bold tracking-tight text-white uppercase leading-none">Achievers</span>
                <span class="text-[10px] text-red-500 font-bold tracking-[0.2em]">INSTITUTE</span>
            </div>
        </a>
        <div class="hidden md:flex items-center space-x-8 text-sm font-medium">
            <a href="/" class="nav-link btn-animate hover:text-red-500 uppercase tracking-widest text-[11px] {% if active_page == 'home' %}active-link text-red-500{% else %}text-white{% endif %}">Home</a>
            <a href="/programs" class="nav-link btn-animate hover:text-red-500 uppercase tracking-widest text-[11px] {% if active_page == 'programs' %}active-link text-red-500{% else %}text-white{% endif %}">Programs</a>
            <a href="/library" class="nav-link btn-animate hover:text-red-500 uppercase tracking-widest text-[11px] {% if active_page == 'library' %}active-link text-red-500{% else %}text-white{% endif %}">Library</a>
            <a href="/faculty" class="nav-link btn-animate hover:text-red-500 uppercase tracking-widest text-[11px] {% if active_page == 'faculty' %}active-link text-red-500{% else %}text-white{% endif %}">Faculty</a>
            {% if 'user_id' not in session %}
            <button onclick="openLoginPopup()" class="btn-animate bg-white text-blue-950 px-6 py-2.5 rounded-full hover:scale-105 active:scale-90 font-bold flex items-center gap-2 shadow-xl uppercase text-[10px] tracking-widest">
                <i data-lucide="user" class="w-3 h-3"></i> Member Login
            </button>
            {% else %}
            <div class="flex items-center gap-4">
                {% if session['role'] == 'admin' %}<a href="/admin-view" class="text-teal-400 text-xs font-bold uppercase hover:underline">Dashboard</a>{% endif %}
                <a href="/logout" class="text-slate-400 hover:text-red-400 transition-colors"><i data-lucide="log-out" class="w-5 h-5"></i></a>
            </div>
            {% endif %}
        </div>
    </div>
</nav>
"""

MODALS_HTML = """
<!-- LEAD CAPTURE POPUP -->
<div id="leadPopup" class="fixed inset-0 z-[200] hidden items-center justify-center p-6">
    <div class="absolute inset-0 bg-blue-950/80 backdrop-blur-md" onclick="closeLeadPopup()"></div>
    <div class="relative bg-white border border-slate-200 rounded-[40px] w-full max-w-md overflow-hidden animate-zoom-in shadow-2xl">
        <button onclick="closeLeadPopup()" class="absolute top-6 right-6 text-slate-400 hover:text-red-600 transition-colors p-2 hover:bg-slate-100 rounded-full z-20">
            <i data-lucide="x" class="w-5 h-5"></i>
        </button>
        <div class="p-10 text-blue-950" id="leadContent">
            <div class="mb-8 text-center md:text-left">
                <h2 class="text-3xl font-bold italic font-serif">Quick Enquiry</h2>
                <p class="text-slate-500 text-sm">Join Najafgarh's elite institute today.</p>
            </div>
            <form id="leadForm" class="space-y-4">
                <input required id="l_name" placeholder="Student Name" class="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3.5 focus:border-red-600 outline-none text-sm">
                <input required id="l_father" placeholder="Father's Name" class="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3.5 focus:border-red-600 outline-none text-sm">
                <input required id="l_class" placeholder="Class / Course" class="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3.5 focus:border-red-600 outline-none text-sm">
                <input required id="l_contact" placeholder="Contact No." class="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3.5 focus:border-red-600 outline-none text-sm">
                <button type="submit" class="btn-animate w-full bg-red-600 text-white font-bold py-4 rounded-xl hover:bg-red-700 active:scale-95 uppercase tracking-widest text-xs">Submit Request</button>
            </form>
        </div>
    </div>
</div>

<!-- LOGIN POPUP -->
<div id="loginPopup" class="fixed inset-0 z-[200] hidden items-center justify-center p-6">
    <div class="absolute inset-0 bg-blue-950/90 backdrop-blur-xl" onclick="closeLoginPopup()"></div>
    <div class="relative bg-white border border-slate-200 rounded-[40px] w-full max-w-md overflow-hidden animate-zoom-in shadow-2xl">
        <button onclick="closeLoginPopup()" class="absolute top-6 right-6 text-slate-400 hover:text-red-600 transition-colors p-2 hover:bg-slate-100 rounded-full z-20">
            <i data-lucide="x" class="w-5 h-5"></i>
        </button>
        <div class="p-10 text-blue-950">
            <h2 class="text-3xl font-bold italic font-serif text-center mb-8">Member Access</h2>
            <form action="/api/login" method="POST">
                <div class="flex bg-slate-100 p-1 rounded-2xl mb-6">
                    <button type="button" onclick="setRole('student')" id="tab-student" class="role-tab active flex-1 py-2 text-[10px] font-bold uppercase rounded-xl">Student</button>
                    <button type="button" onclick="setRole('teacher')" id="tab-teacher" class="role-tab flex-1 py-2 text-[10px] font-bold uppercase rounded-xl">Teacher</button>
                    <button type="button" onclick="setRole('admin')" id="tab-admin" class="role-tab flex-1 py-2 text-[10px] font-bold uppercase rounded-xl">Admin</button>
                </div>
                <input type="hidden" name="role" id="selected-role" value="student">
                <div class="space-y-4 mb-6">
                    <input required name="username" placeholder="Username" class="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-4 focus:border-red-600 outline-none text-sm">
                    <input required name="password" type="password" placeholder="Password" class="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-4 focus:border-red-600 outline-none text-sm">
                </div>
                <button type="submit" class="btn-animate w-full bg-red-600 text-white font-bold py-4 rounded-xl hover:bg-red-700 active:scale-95 uppercase tracking-widest text-xs">Sign In</button>
            </form>
        </div>
    </div>
</div>

<script>
    function setRole(r) {
        document.getElementById('selected-role').value = r;
        document.querySelectorAll('.role-tab').forEach(t => t.classList.remove('active'));
        document.getElementById('tab-' + r).classList.add('active');
    }
    function openLoginPopup() { document.getElementById('loginPopup').classList.remove('hidden'); document.getElementById('loginPopup').classList.add('flex'); }
    function closeLoginPopup() { document.getElementById('loginPopup').classList.add('hidden'); }
    function openLeadPopup() { document.getElementById('leadPopup').classList.remove('hidden'); document.getElementById('leadPopup').classList.add('flex'); }
    function closeLeadPopup() { document.getElementById('leadPopup').classList.add('hidden'); }

    // 15 Second Timer
    setTimeout(() => { if(!sessionStorage.getItem('leadCaptured')) openLeadPopup(); }, 15000);

    // Lead Form Handler
    const leadForm = document.getElementById('leadForm');
    if(leadForm) {
        leadForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const data = {
                name: document.getElementById('l_name').value,
                father_name: document.getElementById('l_father').value,
                course: document.getElementById('l_class').value,
                contact: document.getElementById('l_contact').value
            };
            const res = await fetch('/api/submit', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
            const result = await res.json();
            if(result.status === 'success') {
                sessionStorage.setItem('leadCaptured', 'true');
                document.getElementById('leadContent').innerHTML = `
                <div class="text-center py-12">
                    <i data-lucide="check-circle" class="w-16 h-16 text-green-500 mx-auto mb-6"></i>
                    <h3 class="text-2xl font-bold mb-2">Thank you!</h3>
                    <p class="text-slate-500">We will contact you in <span class="text-red-600 font-bold">2-3 days</span>.</p>
                </div>`;
                lucide.createIcons();
                setTimeout(closeLeadPopup, 4000);
            }
        });
    }
</script>
"""

FOOTER = """
<footer class="py-20 border-t border-white/10 bg-blue-950">
    <div class="max-w-7xl mx-auto px-6 text-center text-white">
        <div class="flex items-center justify-center space-x-2 mb-6">
            <i data-lucide="graduation-cap" class="text-red-500 w-6 h-6"></i>
            <span class="text-xl font-bold tracking-tight uppercase">Achievers</span>
        </div>
        <p class="text-[10px] text-slate-500 uppercase tracking-[0.4em] font-bold">Comprehensive Coaching & Admissions • Najafgarh</p>
    </div>
</footer>
<script>lucide.createIcons();</script>
"""

# --- ROUTES ---
@app.route('/')
def home():
    content = """
    <section class="pt-48 pb-32 max-w-7xl mx-auto px-6 text-center">
        <div class="animate-zoom-in max-w-4xl mx-auto">
            <div class="inline-flex items-center space-x-2 px-4 py-2 rounded-full bg-red-600/10 border border-red-600/20 text-red-500 text-xs font-bold uppercase tracking-widest mb-10">
                <i data-lucide="award" class="w-3 h-3"></i><span>Najafgarh's Academic Leader</span>
            </div>
            <h1 class="text-6xl md:text-9xl font-bold leading-[0.95] mb-10 text-white">Master <br><span class="text-transparent bg-clip-text bg-gradient-to-r from-red-500 to-white">Your Future.</span></h1>
            <p class="text-xl text-slate-300 mb-12 italic leading-relaxed">"As the institute name is Achievers, the student always achieves his/her goal." — Sushil Saini</p>
            <button onclick="openLeadPopup()" class="btn-animate bg-red-600 text-white px-10 py-5 rounded-2xl font-bold hover:scale-105 active:scale-95 shadow-xl uppercase tracking-widest text-xs">Join the Batch</button>
        </div>
    </section>
    """
    return render_template_string(BASE_HEAD + NAVBAR + MODALS_HTML + content + FOOTER, title="Home", active_page="home")

@app.route('/programs')
def programs():
    content = """
    <section class="pt-48 pb-32 max-w-7xl mx-auto px-6">
        <h2 class="text-6xl font-bold mb-16 italic font-serif text-white">Academic Curriculum</h2>
        <div class="grid gap-8">
            <div class="bg-white p-12 rounded-[48px] text-blue-950 shadow-2xl border-l-8 border-red-600">
                <h3 class="text-3xl font-bold mb-4">Classes 1 — 8</h3>
                <p class="text-slate-600">Comprehensive coaching for <strong>all subjects</strong>.</p>
            </div>
            <div class="bg-white p-12 rounded-[48px] text-blue-950 shadow-2xl border-l-8 border-red-600">
                <h3 class="text-3xl font-bold mb-4">Classes 9 — 10</h3>
                <p class="text-slate-600 mb-6">Core subjects: <strong>Science, Maths, English, & Social Science.</strong></p>
                <div class="bg-red-50 text-red-600 p-3 rounded-xl text-xs font-black uppercase tracking-widest inline-flex items-center gap-2"><i data-lucide="clock" class="w-4 h-4"></i> Separate Class Timings Weekly</div>
            </div>
            <div class="bg-white p-12 rounded-[48px] text-blue-950 shadow-2xl border-l-8 border-red-600">
                <h3 class="text-3xl font-bold mb-6">Classes 11 — 12</h3>
                <div class="grid md:grid-cols-2 gap-8 text-sm">
                    <div><h4 class="font-bold text-red-600 uppercase mb-2 tracking-widest">Science Stream</h4><p>Chemistry, Physics, & Mathematics.</p></div>
                    <div><h4 class="font-bold text-red-600 uppercase mb-2 tracking-widest">Commerce Stream</h4><p>Accountancy & Economics.</p></div>
                </div>
                <p class="mt-8 text-slate-500 font-medium">English & other electives available for all streams.</p>
            </div>
        </div>
    </section>
    """
    return render_template_string(BASE_HEAD + NAVBAR + MODALS_HTML + content + FOOTER, title="Programs", active_page="programs")

@app.route('/library')
def library():
    content = """
    <section class="pt-48 pb-32 max-w-7xl mx-auto px-6 grid lg:grid-cols-2 gap-24">
        <div>
            <h2 class="text-6xl font-bold mb-8 italic font-serif text-white">Elite Library</h2>
            <p class="text-xl text-slate-300 leading-relaxed mb-12">Najafgarh's most productive environment.</p>
            <div class="grid grid-cols-2 gap-4">
                <div class="p-6 bg-white rounded-3xl text-blue-950 font-bold uppercase text-[10px]"><i data-lucide="wifi" class="text-red-600 mb-2"></i> High Speed WiFi</div>
                <div class="p-6 bg-white rounded-3xl text-blue-950 font-bold uppercase text-[10px]"><i data-lucide="check" class="text-red-600 mb-2"></i> Daily Maintenance</div>
            </div>
        </div>
        <div class="space-y-6">
            <div class="p-10 bg-white rounded-[40px] text-blue-950 shadow-2xl border-l-8 border-red-600 italic">"Best Library – good space at each desk. Worth it." — Somati</div>
            <div class="p-10 bg-white rounded-[40px] text-blue-950 shadow-2xl border-l-8 border-red-600 italic">"WiFi facility h, environment acha h." — Mansi</div>
        </div>
    </section>
    """
    return render_template_string(BASE_HEAD + NAVBAR + MODALS_HTML + content + FOOTER, title="Library", active_page="library")

@app.route('/faculty')
def faculty():
    content = """
    <section class="pt-48 pb-32 max-w-7xl mx-auto px-6 text-center">
        <h2 class="text-6xl font-bold mb-16 italic font-serif text-white">Our Faculty</h2>
        <div class="grid md:grid-cols-2 gap-12">
            <div class="bg-white p-12 rounded-[64px] text-blue-950 shadow-2xl group transition-all hover:scale-105 border-b-8 border-red-600">
                <div class="w-24 h-24 bg-red-600 rounded-full mx-auto mb-6 flex items-center justify-center shadow-xl"><i data-lucide="user" class="text-white w-10 h-10"></i></div>
                <h3 class="text-2xl font-bold">Arun Sir</h3>
                <p class="text-red-600 font-bold uppercase tracking-widest text-[10px]">Maths Maestro</p>
            </div>
            <div class="bg-white p-12 rounded-[64px] text-blue-950 shadow-2xl group transition-all hover:scale-105 border-b-8 border-red-600">
                <div class="w-24 h-24 bg-blue-900 rounded-full mx-auto mb-6 flex items-center justify-center shadow-xl"><i data-lucide="user-check" class="text-white w-10 h-10"></i></div>
                <h3 class="text-2xl font-bold">Mr. Amit Kumar</h3>
                <p class="text-red-600 font-bold uppercase tracking-widest text-[10px]">English & Social Expert</p>
                <div class="text-left space-y-2 mt-6 text-[10px] font-bold text-slate-600">
                    <p>• English & Spoken English (All Classes)</p>
                    <p>• Social Science (Classes 1-8th)</p>
                    <p>• English Curriculum (Classes 1-12th)</p>
                </div>
            </div>
        </div>
    </section>
    """
    return render_template_string(BASE_HEAD + NAVBAR + MODALS_HTML + content + FOOTER, title="Faculty", active_page="faculty")

@app.route('/api/submit', methods=['POST'])
def submit_lead():
    data = request.json
    new_lead = Lead(name=data['name'], father_name=data['father_name'], course=data['course'], contact=data['contact'])
    db.session.add(new_lead); db.session.commit()
    return jsonify({"status": "success"})

@app.route('/api/login', methods=['POST'])
def api_login():
    user = User.query.filter_by(username=request.form.get('username'), password=request.form.get('password'), role=request.form.get('role')).first()
    if user:
        session['user_id'], session['role'] = user.id, user.role
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('home'))

@app.route('/admin-view')
def admin_view():
    if session.get('role') != 'admin': return "Access Denied"
    leads = Lead.query.order_by(Lead.date_submitted.desc()).all()
    admin_html = """
    <html><head><script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-blue-950 text-white p-10 font-sans">
        <h1 class="text-4xl font-bold mb-10 text-red-500">Collected Leads</h1>
        <table class="w-full border-collapse bg-white text-blue-950 rounded-3xl overflow-hidden shadow-2xl">
            <thead class="bg-slate-100"><tr><th class="p-6 text-left">Name</th><th class="p-6 text-left">Father</th><th class="p-6 text-left">Class</th><th class="p-6 text-left">Contact</th></tr></thead>
            <tbody>{% for l in leads %}<tr class="border-t">
                <td class="p-6 font-bold">{{ l.name }}</td><td class="p-6">{{ l.father_name }}</td><td class="p-6 text-red-600">{{ l.course }}</td><td class="p-6">{{ l.contact }}</td>
            </tr>{% endfor %}</tbody>
        </table>
    </body></html>"""
    return render_template_string(admin_html, leads=leads)

if __name__ == '__main__':
    app.run(debug=True)
