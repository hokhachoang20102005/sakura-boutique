from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class NguoiDung(UserMixin, db.Model):
    __tablename__ = 'nguoi_dung'

    id = db.Column(db.Integer, primary_key=True)
    ten_dang_nhap = db.Column(db.Unicode(50), unique=True, nullable=False)
    email = db.Column(db.Unicode(120), unique=True, nullable=False)
    mat_khau_hash = db.Column(db.Unicode(256), nullable=False)
    ho_ten = db.Column(db.Unicode(100), nullable=False)
    sdt = db.Column(db.Unicode(20))
    la_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    vi = db.relationship('Vi', backref='chu_so_huu', uselist=False)
    san_pham = db.relationship('SanPham', backref='nguoi_ban')
    don_hang = db.relationship('DonHang', backref='nguoi_mua', foreign_keys='DonHang.nguoi_mua_id')
    yeu_cau_nap = db.relationship('YeuCauNap', backref='nguoi_dung')

    def dat_mat_khau(self, mat_khau):
        self.mat_khau_hash = generate_password_hash(mat_khau)

    def kiem_tra_mat_khau(self, mat_khau):
        return check_password_hash(self.mat_khau_hash, mat_khau)


class Vi(db.Model):
    __tablename__ = 'vi'

    id = db.Column(db.Integer, primary_key=True)
    nguoi_dung_id = db.Column(db.Integer, db.ForeignKey('nguoi_dung.id'), unique=True, nullable=False)
    so_du = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)

    giao_dich = db.relationship('GiaoDichVi', backref='vi')
    chuyen_di = db.relationship('ChuyenTien', backref='vi_gui', foreign_keys='ChuyenTien.vi_gui_id')
    chuyen_den = db.relationship('ChuyenTien', backref='vi_nhan', foreign_keys='ChuyenTien.vi_nhan_id')


class GiaoDichVi(db.Model):
    __tablename__ = 'giao_dich_vi'

    id = db.Column(db.Integer, primary_key=True)
    vi_id = db.Column(db.Integer, db.ForeignKey('vi.id'), nullable=False)
    loai = db.Column(db.Unicode(20), nullable=False)
    so_tien = db.Column(db.Integer, nullable=False)
    so_du_sau = db.Column(db.Integer, nullable=False)
    mo_ta = db.Column(db.Unicode(200))
    don_hang_id = db.Column(db.Integer, db.ForeignKey('don_hang.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)


class YeuCauNap(db.Model):
    __tablename__ = 'yeu_cau_nap'

    id = db.Column(db.Integer, primary_key=True)
    nguoi_dung_id = db.Column(db.Integer, db.ForeignKey('nguoi_dung.id'), nullable=False)
    so_tien = db.Column(db.Integer, nullable=False)
    ma_giao_dich = db.Column(db.Unicode(50), unique=True, nullable=False)
    trang_thai = db.Column(db.Unicode(20), default='cho_duyet')
    ghi_chu_admin = db.Column(db.Unicode(200))
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)


class SanPham(db.Model):
    __tablename__ = 'san_pham'

    id = db.Column(db.Integer, primary_key=True)
    nguoi_ban_id = db.Column(db.Integer, db.ForeignKey('nguoi_dung.id'), nullable=False)
    ten = db.Column(db.Unicode(200), nullable=False)
    mo_ta = db.Column(db.UnicodeText)
    gia = db.Column(db.Integer, nullable=False)
    gia_goc = db.Column(db.Integer, nullable=True)
    danh_muc = db.Column(db.Unicode(50), nullable=False)
    kich_co = db.Column(db.Unicode(100))
    mau_sac = db.Column(db.Unicode(100))
    chat_lieu = db.Column(db.Unicode(100))
    so_luong = db.Column(db.Integer, default=0)
    anh = db.Column(db.Unicode(200))
    dang_ban = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)


class DonHang(db.Model):
    __tablename__ = 'don_hang'

    id = db.Column(db.Integer, primary_key=True)
    nguoi_mua_id = db.Column(db.Integer, db.ForeignKey('nguoi_dung.id'), nullable=False)
    san_pham_id = db.Column(db.Integer, db.ForeignKey('san_pham.id'), nullable=False)
    so_luong = db.Column(db.Integer, nullable=False)
    kich_co_chon = db.Column(db.Unicode(10))
    mau_sac_chon = db.Column(db.Unicode(20))
    tong_tien = db.Column(db.Integer, nullable=False)
    dia_chi_giao = db.Column(db.Unicode(500))
    trang_thai = db.Column(db.Unicode(20), default='cho_xu_ly')
    created_at = db.Column(db.DateTime, default=datetime.now)

    san_pham = db.relationship('SanPham', backref='don_hang')


class YeuCauRut(db.Model):
    __tablename__ = 'yeu_cau_rut'

    id = db.Column(db.Integer, primary_key=True)
    nguoi_dung_id = db.Column(db.Integer, db.ForeignKey('nguoi_dung.id'), nullable=False)
    so_tien = db.Column(db.Integer, nullable=False)
    ngan_hang = db.Column(db.Unicode(100), nullable=False)
    so_tai_khoan = db.Column(db.Unicode(50), nullable=False)
    ten_tai_khoan = db.Column(db.Unicode(100), nullable=False)
    trang_thai = db.Column(db.Unicode(20), default='cho_duyet')
    ghi_chu_admin = db.Column(db.Unicode(200))
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    nguoi_dung = db.relationship('NguoiDung', backref='ds_yeu_cau_rut')


class ChuyenTien(db.Model):
    __tablename__ = 'chuyen_tien'

    id = db.Column(db.Integer, primary_key=True)
    vi_gui_id = db.Column(db.Integer, db.ForeignKey('vi.id'), nullable=False)
    vi_nhan_id = db.Column(db.Integer, db.ForeignKey('vi.id'), nullable=False)
    so_tien = db.Column(db.Integer, nullable=False)
    ghi_chu = db.Column(db.Unicode(200))
    created_at = db.Column(db.DateTime, default=datetime.now)
