import os
import uuid
import io
import qrcode
import base64
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from cau_hinh import CauHinh
from mo_hinh import db, NguoiDung, Vi, GiaoDichVi, YeuCauNap, YeuCauRut, SanPham, DonHang, ChuyenTien

app = Flask(__name__)
app.config.from_object(CauHinh)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'dang_nhap'
login_manager.login_message = 'Vui lòng đăng nhập để tiếp tục.'


@login_manager.user_loader
def tai_nguoi_dung(user_id):
    return NguoiDung.query.get(int(user_id))


DUOI_FILE_HOP_LE = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def file_hop_le(ten_file):
    return '.' in ten_file and ten_file.rsplit('.', 1)[1].lower() in DUOI_FILE_HOP_LE

def dinh_dang_tien(so):
    if so is None:
        return '0'
    return '{:,.0f}'.format(so).replace(',', '.')

DANH_MUC = {
    'vay': 'Váy',
    'dam': 'Đầm',
    'tui_xach': 'Túi xách',
    'guoc_giay': 'Guốc & Giày',
    'ao': 'Áo',
    'phu_kien': 'Phụ kiện',
    'khac': 'Khác',
}

TRANG_THAI_DON = {
    'cho_xu_ly': 'Chờ xử lý',
    'da_thanh_toan': 'Đã thanh toán',
    'dang_giao': 'Đang giao',
    'hoan_thanh': 'Hoàn thành',
    'da_hoan_tien': 'Đã hoàn tiền',
    'da_huy': 'Đã huỷ',
}

LOAI_GIAO_DICH = {
    'nap_tien': 'Nạp tiền',
    'rut_tien': 'Rút tiền',
    'thanh_toan': 'Thanh toán',
    'hoan_tien': 'Hoàn tiền',
    'nhan_tien': 'Nhận tiền',
    'chuyen_tien': 'Chuyển tiền',
}


@app.context_processor
def tien_ich():
    return dict(
        dinh_dang_tien=dinh_dang_tien,
        DANH_MUC=DANH_MUC,
        TRANG_THAI_DON=TRANG_THAI_DON,
        LOAI_GIAO_DICH=LOAI_GIAO_DICH,
    )


# ============================================================
# AUTH
# ============================================================

@app.route('/dang-ky', methods=['GET', 'POST'])
def dang_ky():
    if current_user.is_authenticated:
        return redirect(url_for('trang_chu'))
    if request.method == 'POST':
        ten = request.form['ten_dang_nhap'].strip()
        email = request.form['email'].strip()
        mat_khau = request.form['mat_khau']
        ho_ten = request.form['ho_ten'].strip()
        sdt = request.form.get('sdt', '').strip()

        if NguoiDung.query.filter_by(ten_dang_nhap=ten).first():
            flash('Tên đăng nhập đã tồn tại.', 'danger')
            return redirect(url_for('dang_ky'))
        if NguoiDung.query.filter_by(email=email).first():
            flash('Email đã được sử dụng.', 'danger')
            return redirect(url_for('dang_ky'))

        nguoi_dung = NguoiDung(ten_dang_nhap=ten, email=email, ho_ten=ho_ten, sdt=sdt)
        nguoi_dung.dat_mat_khau(mat_khau)
        db.session.add(nguoi_dung)
        db.session.flush()

        vi = Vi(nguoi_dung_id=nguoi_dung.id)
        db.session.add(vi)
        db.session.commit()

        flash('Đăng ký thành công! Hãy đăng nhập.', 'success')
        return redirect(url_for('dang_nhap'))
    return render_template('dang_ky.html')


@app.route('/dang-nhap', methods=['GET', 'POST'])
def dang_nhap():
    if current_user.is_authenticated:
        return redirect(url_for('trang_chu'))
    if request.method == 'POST':
        ten = request.form['ten_dang_nhap'].strip()
        mat_khau = request.form['mat_khau']
        nguoi_dung = NguoiDung.query.filter_by(ten_dang_nhap=ten).first()
        if nguoi_dung and nguoi_dung.kiem_tra_mat_khau(mat_khau):
            login_user(nguoi_dung)
            flash('Đăng nhập thành công!', 'success')
            trang_tiep = request.args.get('next')
            return redirect(trang_tiep or url_for('trang_chu'))
        flash('Tên đăng nhập hoặc mật khẩu không đúng.', 'danger')
    return render_template('dang_nhap.html')


@app.route('/dang-xuat')
@login_required
def dang_xuat():
    logout_user()
    flash('Đã đăng xuất.', 'info')
    return redirect(url_for('trang_chu'))


# ============================================================
# TRANG CHU + SAN PHAM
# ============================================================

@app.route('/shop-by-look')
def shop_by_look():
    lookbook_dir = os.path.join(app.static_folder, 'uploads', 'lookbook')
    ds_anh = []
    if os.path.isdir(lookbook_dir):
        ds_anh = sorted([f for f in os.listdir(lookbook_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))])
    return render_template('shop_by_look.html', ds_anh=ds_anh)


@app.route('/')
def trang_chu():
    danh_muc_loc = request.args.get('danh_muc', '')
    gia_min = request.args.get('gia_min', type=int)
    gia_max = request.args.get('gia_max', type=int)
    tim_kiem = request.args.get('q', '').strip()

    truy_van = SanPham.query.filter_by(dang_ban=True)
    if danh_muc_loc:
        truy_van = truy_van.filter_by(danh_muc=danh_muc_loc)
    if gia_min is not None:
        truy_van = truy_van.filter(SanPham.gia >= gia_min)
    if gia_max is not None:
        truy_van = truy_van.filter(SanPham.gia <= gia_max)
    if tim_kiem:
        truy_van = truy_van.filter(SanPham.ten.ilike(f'%{tim_kiem}%'))

    sap_xep = request.args.get('sap_xep', '')
    if sap_xep == 'gia_tang':
        truy_van = truy_van.order_by(SanPham.gia.asc())
    elif sap_xep == 'gia_giam':
        truy_van = truy_van.order_by(SanPham.gia.desc())
    else:
        truy_van = truy_van.order_by(SanPham.created_at.desc())

    ds_san_pham = truy_van.all()
    return render_template('trang_chu.html', ds_san_pham=ds_san_pham, danh_muc_loc=danh_muc_loc)


@app.route('/san-pham/<int:sp_id>')
def chi_tiet_san_pham(sp_id):
    sp = SanPham.query.get_or_404(sp_id)
    ds_kich_co = [s.strip() for s in sp.kich_co.split(',')] if sp.kich_co else []
    ds_mau_sac = [m.strip() for m in sp.mau_sac.split(',')] if sp.mau_sac else []
    return render_template('chi_tiet_sp.html', sp=sp, ds_kich_co=ds_kich_co, ds_mau_sac=ds_mau_sac)


@app.route('/dang-ban', methods=['GET', 'POST'])
@login_required
def dang_ban():
    if request.method == 'POST':
        anh_file = request.files.get('anh')
        ten_anh = None
        if anh_file and anh_file.filename and file_hop_le(anh_file.filename):
            ten_anh = str(uuid.uuid4()) + '.' + anh_file.filename.rsplit('.', 1)[1].lower()
            anh_file.save(os.path.join(app.config['UPLOAD_FOLDER'], ten_anh))

        gia_goc_str = request.form.get('gia_goc', '').strip()
        gia_goc = int(gia_goc_str) if gia_goc_str else None

        sp = SanPham(
            nguoi_ban_id=current_user.id,
            ten=request.form['ten'].strip(),
            mo_ta=request.form.get('mo_ta', '').strip(),
            gia=int(request.form['gia']),
            gia_goc=gia_goc,
            danh_muc=request.form['danh_muc'],
            kich_co=request.form.get('kich_co', '').strip(),
            mau_sac=request.form.get('mau_sac', '').strip(),
            chat_lieu=request.form.get('chat_lieu', '').strip(),
            so_luong=int(request.form.get('so_luong', 1)),
            anh=ten_anh,
        )
        db.session.add(sp)
        db.session.commit()
        flash('Đăng bán sản phẩm thành công!', 'success')
        return redirect(url_for('sp_cua_toi'))
    return render_template('dang_ban.html')


@app.route('/sp-cua-toi')
@login_required
def sp_cua_toi():
    ds = SanPham.query.filter_by(nguoi_ban_id=current_user.id).order_by(SanPham.created_at.desc()).all()
    return render_template('sp_cua_toi.html', ds_san_pham=ds)


@app.route('/sua-sp/<int:sp_id>', methods=['GET', 'POST'])
@login_required
def sua_san_pham(sp_id):
    sp = SanPham.query.get_or_404(sp_id)
    if sp.nguoi_ban_id != current_user.id:
        flash('Bạn không có quyền sửa sản phẩm này.', 'danger')
        return redirect(url_for('sp_cua_toi'))

    if request.method == 'POST':
        sp.ten = request.form['ten'].strip()
        sp.mo_ta = request.form.get('mo_ta', '').strip()
        sp.gia = int(request.form['gia'])
        gia_goc_str = request.form.get('gia_goc', '').strip()
        sp.gia_goc = int(gia_goc_str) if gia_goc_str else None
        sp.danh_muc = request.form['danh_muc']
        sp.kich_co = request.form.get('kich_co', '').strip()
        sp.mau_sac = request.form.get('mau_sac', '').strip()
        sp.chat_lieu = request.form.get('chat_lieu', '').strip()
        sp.so_luong = int(request.form.get('so_luong', 1))
        sp.dang_ban = 'dang_ban' in request.form

        anh_file = request.files.get('anh')
        if anh_file and anh_file.filename and file_hop_le(anh_file.filename):
            ten_anh = str(uuid.uuid4()) + '.' + anh_file.filename.rsplit('.', 1)[1].lower()
            anh_file.save(os.path.join(app.config['UPLOAD_FOLDER'], ten_anh))
            sp.anh = ten_anh

        db.session.commit()
        flash('Đã cập nhật sản phẩm.', 'success')
        return redirect(url_for('sp_cua_toi'))
    return render_template('dang_ban.html', sp=sp, la_sua=True)


@app.route('/xoa-sp/<int:sp_id>')
@login_required
def xoa_san_pham(sp_id):
    sp = SanPham.query.get_or_404(sp_id)
    if sp.nguoi_ban_id != current_user.id:
        flash('Bạn không có quyền ẩn sản phẩm này.', 'danger')
        return redirect(url_for('sp_cua_toi'))
    sp.dang_ban = False
    db.session.commit()
    flash('Đã ẩn sản phẩm.', 'info')
    return redirect(url_for('sp_cua_toi'))


# ============================================================
# VI DIEN TU
# ============================================================

@app.route('/vi-tien')
@login_required
def vi_tien():
    vi = current_user.vi
    ds_giao_dich = GiaoDichVi.query.filter_by(vi_id=vi.id).order_by(GiaoDichVi.created_at.desc()).limit(50).all()
    ds_yeu_cau = YeuCauNap.query.filter_by(nguoi_dung_id=current_user.id).order_by(YeuCauNap.created_at.desc()).limit(20).all()
    return render_template('vi_tien.html', vi=vi, ds_giao_dich=ds_giao_dich, ds_yeu_cau=ds_yeu_cau)


@app.route('/nap-tien', methods=['GET', 'POST'])
@login_required
def nap_tien():
    if request.method == 'POST':
        so_tien = int(request.form['so_tien'])
        if so_tien < 10000:
            flash('Số tiền nạp tối thiểu là 10.000đ.', 'danger')
            return redirect(url_for('nap_tien'))

        ma_gd = 'SK' + uuid.uuid4().hex[:8].upper()
        yeu_cau = YeuCauNap(
            nguoi_dung_id=current_user.id,
            so_tien=so_tien,
            ma_giao_dich=ma_gd,
        )
        db.session.add(yeu_cau)
        db.session.commit()

        noi_dung_ck = ma_gd
        qr_data = tao_vietqr(so_tien, noi_dung_ck)

        return render_template('nap_tien.html', qr_data=qr_data, ma_gd=ma_gd, so_tien=so_tien, da_tao=True)

    return render_template('nap_tien.html', da_tao=False)


def tao_vietqr(so_tien, noi_dung):
    ngan_hang = app.config['NGAN_HANG']
    stk = app.config['SO_TAI_KHOAN']
    ten_tk = app.config['TEN_TAI_KHOAN']

    url_qr = f"https://img.vietqr.io/image/{ngan_hang}-{stk}-compact.png?amount={so_tien}&addInfo={noi_dung}&accountName={ten_tk}"
    return url_qr


@app.route('/rut-tien', methods=['GET', 'POST'])
@login_required
def rut_tien():
    if request.method == 'POST':
        so_tien = int(request.form['so_tien'])
        ngan_hang = request.form['ngan_hang'].strip()
        so_tai_khoan = request.form['so_tai_khoan'].strip()
        ten_tai_khoan = request.form['ten_tai_khoan'].strip()

        if so_tien < 10000:
            flash('Số tiền rút tối thiểu là 10.000đ.', 'danger')
            return redirect(url_for('rut_tien'))
        if current_user.vi.so_du < so_tien:
            flash('Số dư không đủ.', 'danger')
            return redirect(url_for('rut_tien'))

        yc = YeuCauRut(nguoi_dung_id=current_user.id, so_tien=so_tien,
                       ngan_hang=ngan_hang, so_tai_khoan=so_tai_khoan, ten_tai_khoan=ten_tai_khoan)
        db.session.add(yc)
        db.session.commit()

        flash(f'Đã gửi yêu cầu rút {dinh_dang_tien(so_tien)}đ. Vui lòng chờ admin duyệt.', 'success')
        return redirect(url_for('vi_tien'))

    ds_yeu_cau = YeuCauRut.query.filter_by(nguoi_dung_id=current_user.id).order_by(YeuCauRut.created_at.desc()).limit(20).all()
    return render_template('rut_tien.html', ds_yeu_cau=ds_yeu_cau)


# ============================================================
# DON HANG
# ============================================================

@app.route('/mua-hang/<int:sp_id>', methods=['POST'])
@login_required
def mua_hang(sp_id):
    sp = SanPham.query.get_or_404(sp_id)
    if sp.nguoi_ban_id == current_user.id:
        flash('Bạn không thể mua sản phẩm của chính mình.', 'danger')
        return redirect(url_for('chi_tiet_san_pham', sp_id=sp_id))

    so_luong = int(request.form.get('so_luong', 1))
    kich_co = request.form.get('kich_co', '')
    mau_sac = request.form.get('mau_sac', '')
    dia_chi = request.form.get('dia_chi', '').strip()

    if so_luong > sp.so_luong:
        flash('Số lượng tồn kho không đủ.', 'danger')
        return redirect(url_for('chi_tiet_san_pham', sp_id=sp_id))

    tong_tien = sp.gia * so_luong
    vi = current_user.vi

    if vi.so_du < tong_tien:
        flash(f'Số dư ví không đủ. Cần {dinh_dang_tien(tong_tien)}đ, hiện có {dinh_dang_tien(vi.so_du)}đ.', 'danger')
        return redirect(url_for('chi_tiet_san_pham', sp_id=sp_id))

    vi.so_du -= tong_tien

    don = DonHang(
        nguoi_mua_id=current_user.id,
        san_pham_id=sp.id,
        so_luong=so_luong,
        kich_co_chon=kich_co,
        mau_sac_chon=mau_sac,
        tong_tien=tong_tien,
        dia_chi_giao=dia_chi,
        trang_thai='cho_xu_ly',
    )
    db.session.add(don)
    db.session.flush()

    gd = GiaoDichVi(vi_id=vi.id, loai='thanh_toan', so_tien=-tong_tien,
                    so_du_sau=vi.so_du, mo_ta=f'Thanh toán đơn hàng #{don.id}', don_hang_id=don.id)
    db.session.add(gd)

    sp.so_luong -= so_luong
    db.session.commit()

    flash(f'Đặt hàng thành công! Đơn hàng #{don.id}', 'success')
    return redirect(url_for('chi_tiet_don_hang', dh_id=don.id))


@app.route('/don-hang')
@login_required
def don_hang():
    ds_mua = DonHang.query.filter_by(nguoi_mua_id=current_user.id).order_by(DonHang.created_at.desc()).all()
    ds_ban = DonHang.query.join(SanPham).filter(SanPham.nguoi_ban_id == current_user.id).order_by(DonHang.created_at.desc()).all()
    return render_template('don_hang.html', ds_mua=ds_mua, ds_ban=ds_ban)


@app.route('/don-hang/<int:dh_id>')
@login_required
def chi_tiet_don_hang(dh_id):
    don = DonHang.query.get_or_404(dh_id)
    la_nguoi_mua = don.nguoi_mua_id == current_user.id
    la_nguoi_ban = don.san_pham.nguoi_ban_id == current_user.id
    if not la_nguoi_mua and not la_nguoi_ban and not current_user.la_admin:
        flash('Bạn không có quyền xem đơn hàng này.', 'danger')
        return redirect(url_for('don_hang'))
    return render_template('chi_tiet_dh.html', don=don, la_nguoi_mua=la_nguoi_mua, la_nguoi_ban=la_nguoi_ban)


@app.route('/cap-nhat-don/<int:dh_id>/<hanh_dong>')
@login_required
def cap_nhat_don_hang(dh_id, hanh_dong):
    don = DonHang.query.get_or_404(dh_id)
    la_nguoi_ban = don.san_pham.nguoi_ban_id == current_user.id
    la_nguoi_mua = don.nguoi_mua_id == current_user.id

    if hanh_dong == 'xac-nhan' and la_nguoi_ban and don.trang_thai == 'cho_xu_ly':
        don.trang_thai = 'da_thanh_toan'
        flash('Đã xác nhận đơn hàng.', 'success')

    elif hanh_dong == 'giao-hang' and la_nguoi_ban and don.trang_thai == 'da_thanh_toan':
        don.trang_thai = 'dang_giao'
        flash('Đã chuyển sang trạng thái đang giao.', 'success')

    elif hanh_dong == 'nhan-hang' and la_nguoi_mua and don.trang_thai == 'dang_giao':
        don.trang_thai = 'hoan_thanh'
        vi_ban = don.san_pham.nguoi_ban.vi
        vi_ban.so_du += don.tong_tien
        gd = GiaoDichVi(vi_id=vi_ban.id, loai='nhan_tien', so_tien=don.tong_tien,
                        so_du_sau=vi_ban.so_du, mo_ta=f'Nhận tiền đơn hàng #{don.id}', don_hang_id=don.id)
        db.session.add(gd)
        flash('Đã xác nhận nhận hàng. Tiền đã chuyển cho người bán.', 'success')

    elif hanh_dong == 'huy' and la_nguoi_mua and don.trang_thai in ('cho_xu_ly', 'da_thanh_toan'):
        don.trang_thai = 'da_huy'
        vi_mua = current_user.vi
        vi_mua.so_du += don.tong_tien
        gd = GiaoDichVi(vi_id=vi_mua.id, loai='hoan_tien', so_tien=don.tong_tien,
                        so_du_sau=vi_mua.so_du, mo_ta=f'Hoàn tiền đơn hàng #{don.id}', don_hang_id=don.id)
        db.session.add(gd)
        sp = don.san_pham
        sp.so_luong += don.so_luong
        flash('Đã huỷ đơn hàng. Tiền đã hoàn vào ví.', 'info')

    else:
        flash('Không thể thực hiện hành động này.', 'danger')

    db.session.commit()
    return redirect(url_for('chi_tiet_don_hang', dh_id=dh_id))


# ============================================================
# ADMIN — DUYET NAP TIEN
# ============================================================

@app.route('/admin')
@login_required
def admin_panel():
    if not current_user.la_admin:
        flash('Bạn không có quyền truy cập.', 'danger')
        return redirect(url_for('trang_chu'))
    return render_template('admin_panel.html')


@app.route('/webhook/sepay', methods=['POST'])
def webhook_sepay():
    api_key = app.config.get('SEPAY_API_KEY', '')
    if api_key:
        auth = request.headers.get('Authorization', '')
        if auth != f'Apikey {api_key}':
            return jsonify(success=False), 403

    data = request.get_json(silent=True)
    if not data or data.get('transferType') != 'in':
        return jsonify(success=True), 200

    noi_dung = (data.get('content') or '').upper()
    so_tien = int(data.get('transferAmount', 0))

    yc = YeuCauNap.query.filter_by(trang_thai='cho_duyet').filter(
        db.func.upper(YeuCauNap.ma_giao_dich) == noi_dung
    ).first()
    if not yc:
        for y in YeuCauNap.query.filter_by(trang_thai='cho_duyet').all():
            if y.ma_giao_dich.upper() in noi_dung:
                yc = y
                break
    if not yc:
        return jsonify(success=True), 200

    if so_tien < yc.so_tien:
        return jsonify(success=True), 200

    yc.trang_thai = 'da_duyet'
    yc.ghi_chu_admin = f'SePay tự động — ref: {data.get("referenceCode", "")}'
    yc.updated_at = datetime.now()

    vi = Vi.query.filter_by(nguoi_dung_id=yc.nguoi_dung_id).first()
    vi.so_du += yc.so_tien
    gd = GiaoDichVi(vi_id=vi.id, loai='nap_tien', so_tien=yc.so_tien,
                    so_du_sau=vi.so_du, mo_ta=f'Nạp tiền — Mã GD: {yc.ma_giao_dich}')
    db.session.add(gd)
    db.session.commit()
    return jsonify(success=True), 200


@app.route('/admin/duyet-nap')
@login_required
def admin_duyet_nap():
    if not current_user.la_admin:
        flash('Bạn không có quyền truy cập.', 'danger')
        return redirect(url_for('trang_chu'))
    ds = YeuCauNap.query.order_by(YeuCauNap.created_at.desc()).all()
    return render_template('admin_duyet_nap.html', ds_yeu_cau=ds)


@app.route('/admin/duyet-nap/<int:yc_id>/<hanh_dong>', methods=['POST'])
@login_required
def xu_ly_nap(yc_id, hanh_dong):
    if not current_user.la_admin:
        flash('Bạn không có quyền.', 'danger')
        return redirect(url_for('trang_chu'))

    yc = YeuCauNap.query.get_or_404(yc_id)
    if yc.trang_thai != 'cho_duyet':
        flash('Yêu cầu này đã được xử lý.', 'info')
        return redirect(url_for('admin_duyet_nap'))

    ghi_chu = request.form.get('ghi_chu', '').strip()

    if hanh_dong == 'duyet':
        yc.trang_thai = 'da_duyet'
        yc.ghi_chu_admin = ghi_chu
        yc.updated_at = datetime.now()

        vi = Vi.query.filter_by(nguoi_dung_id=yc.nguoi_dung_id).first()
        vi.so_du += yc.so_tien
        gd = GiaoDichVi(vi_id=vi.id, loai='nap_tien', so_tien=yc.so_tien,
                        so_du_sau=vi.so_du, mo_ta=f'Nạp tiền — Mã GD: {yc.ma_giao_dich}')
        db.session.add(gd)
        flash(f'Đã duyệt nạp {dinh_dang_tien(yc.so_tien)}đ cho {yc.nguoi_dung.ho_ten}.', 'success')

    elif hanh_dong == 'tu-choi':
        yc.trang_thai = 'tu_choi'
        yc.ghi_chu_admin = ghi_chu
        yc.updated_at = datetime.now()
        flash('Đã từ chối yêu cầu nạp tiền.', 'info')

    db.session.commit()
    return redirect(url_for('admin_duyet_nap'))


@app.route('/admin/duyet-rut')
@login_required
def admin_duyet_rut():
    if not current_user.la_admin:
        flash('Bạn không có quyền truy cập.', 'danger')
        return redirect(url_for('trang_chu'))
    ds = YeuCauRut.query.order_by(YeuCauRut.created_at.desc()).all()
    return render_template('admin_duyet_rut.html', ds_yeu_cau=ds)


@app.route('/admin/duyet-rut/<int:yc_id>/<hanh_dong>', methods=['POST'])
@login_required
def xu_ly_rut(yc_id, hanh_dong):
    if not current_user.la_admin:
        flash('Bạn không có quyền.', 'danger')
        return redirect(url_for('trang_chu'))

    yc = YeuCauRut.query.get_or_404(yc_id)
    if yc.trang_thai != 'cho_duyet':
        flash('Yêu cầu này đã được xử lý.', 'info')
        return redirect(url_for('admin_duyet_rut'))

    ghi_chu = request.form.get('ghi_chu', '').strip()

    if hanh_dong == 'duyet':
        vi = Vi.query.filter_by(nguoi_dung_id=yc.nguoi_dung_id).first()
        if vi.so_du < yc.so_tien:
            flash(f'Số dư ví không đủ ({dinh_dang_tien(vi.so_du)}đ < {dinh_dang_tien(yc.so_tien)}đ).', 'danger')
            return redirect(url_for('admin_duyet_rut'))

        yc.trang_thai = 'da_duyet'
        yc.ghi_chu_admin = ghi_chu
        yc.updated_at = datetime.now()

        vi.so_du -= yc.so_tien
        gd = GiaoDichVi(vi_id=vi.id, loai='rut_tien', so_tien=-yc.so_tien,
                        so_du_sau=vi.so_du,
                        mo_ta=f'Rút tiền về {yc.ngan_hang} — STK: {yc.so_tai_khoan}')
        db.session.add(gd)
        flash(f'Đã duyệt rút {dinh_dang_tien(yc.so_tien)}đ cho {yc.nguoi_dung.ho_ten}.', 'success')

    elif hanh_dong == 'tu-choi':
        yc.trang_thai = 'tu_choi'
        yc.ghi_chu_admin = ghi_chu
        yc.updated_at = datetime.now()
        flash('Đã từ chối yêu cầu rút tiền.', 'info')

    db.session.commit()
    return redirect(url_for('admin_duyet_rut'))


# ============================================================
# ADMIN — XEM CSDL
# ============================================================

@app.route('/admin/csdl')
@login_required
def admin_csdl():
    if not current_user.la_admin:
        flash('Bạn không có quyền truy cập.', 'danger')
        return redirect(url_for('trang_chu'))

    bang_chon = request.args.get('bang', '')
    ds_bang = {
        'nguoi_dung': {'model': NguoiDung, 'ten': 'Người dùng'},
        'vi': {'model': Vi, 'ten': 'Ví'},
        'giao_dich_vi': {'model': GiaoDichVi, 'ten': 'Giao dịch ví'},
        'yeu_cau_nap': {'model': YeuCauNap, 'ten': 'Yêu cầu nạp'},
        'san_pham': {'model': SanPham, 'ten': 'Sản phẩm'},
        'don_hang': {'model': DonHang, 'ten': 'Đơn hàng'},
        'yeu_cau_rut': {'model': YeuCauRut, 'ten': 'Yêu cầu rút'},
        'chuyen_tien': {'model': ChuyenTien, 'ten': 'Chuyển tiền'},
    }

    du_lieu = []
    ten_cot = []
    if bang_chon and bang_chon in ds_bang:
        model = ds_bang[bang_chon]['model']
        ten_cot = [c.name for c in model.__table__.columns]
        tat_ca = model.query.all()
        for dong in tat_ca:
            du_lieu.append([getattr(dong, c) for c in ten_cot])

    quan_he = []
    for ten_bang, info in ds_bang.items():
        model = info['model']
        for col in model.__table__.columns:
            for fk in col.foreign_keys:
                quan_he.append({
                    'tu_bang': ten_bang,
                    'tu_cot': col.name,
                    'den_bang': fk.column.table.name,
                    'den_cot': fk.column.name,
                })

    return render_template('admin_csdl.html', ds_bang=ds_bang, bang_chon=bang_chon,
                           ten_cot=ten_cot, du_lieu=du_lieu, quan_he=quan_he)


# ============================================================
# KHOI TAO
# ============================================================

with app.app_context():
    db.create_all()
    if not NguoiDung.query.filter_by(la_admin=True).first():
        admin = NguoiDung(ten_dang_nhap='admin', email='admin@sakura.vn',
                          ho_ten='Admin Sakura', la_admin=True)
        admin.dat_mat_khau('admin123')
        db.session.add(admin)
        db.session.flush()
        vi_admin = Vi(nguoi_dung_id=admin.id)
        db.session.add(vi_admin)
        db.session.commit()

    if SanPham.query.count() == 0:
        admin = NguoiDung.query.filter_by(la_admin=True).first()
        DS_SP = [
            ("Set Khánh Niên – BST Lễ Hội", 785000, 1570000, "dam", "Lụa tổng hợp", "sp_mau_00.jpg"),
            ("Áo dài Bảo Diên – BST Lễ Hội", 1275000, None, "ao", "Lụa", "sp_mau_01.jpg"),
            ("Áo Nhật Chiêu – BST Lễ Hội", 1250000, None, "ao", "Vải thô", "sp_mau_02.jpg"),
            ("Áo Hồng Tiêu – BST Lễ Hội", 685000, None, "ao", "Cotton", "sp_mau_03.jpg"),
            ("Khăn Lạc Phong – BST Lễ Hội", 375000, None, "phu_kien", "Lụa", "sp_mau_04.jpg"),
            ("Khăn Cát Cát – BST Lễ Hội", 575000, None, "phu_kien", "Lụa tơ tằm", "sp_mau_05.jpg"),
            ("Đầm Tiêu Y – Thạch – BST Lễ Hội", 465000, None, "dam", "Vải lanh", "sp_mau_06.jpg"),
            ("Quần Hoa Phong – Mẫu Đơn – BST Lễ Hội", 675000, None, "vay", "Cotton pha", "sp_mau_07.jpg"),
            ("Khăn Hạ Y – BST Lễ Hội", 245000, None, "phu_kien", "Vải thô", "sp_mau_08.jpg"),
            ("Áo dài Lưu Thảo", 975000, None, "ao", "Lụa", "sp_mau_09.jpg"),
            ("Áo khoác Kiển Sam", 1650000, None, "ao", "Dạ", "sp_mau_10.jpg"),
            ("Áo dài Kim Châu", 985000, 1085000, "ao", "Lụa gấm", "sp_mau_11.jpg"),
            ("Quần Hoa Phong – Kim Sa", 745000, None, "vay", "Cotton pha", "sp_mau_12.jpg"),
            ("Áo dài Bảo Diên", 1275000, None, "ao", "Lụa", "sp_mau_13.jpg"),
            ("Đầm Tiêu Y – Kết", 575000, None, "dam", "Vải lanh", "sp_mau_14.jpg"),
            ("Đầm Tiêu Y – Lý", 525000, None, "dam", "Vải lanh", "sp_mau_15.jpg"),
            ("Đầm Tiêu Y – Ngân", 525000, None, "dam", "Vải lanh", "sp_mau_16.jpg"),
            ("Khăn Lạc Phong", 375000, None, "phu_kien", "Lụa", "sp_mau_17.jpg"),
            ("Khăn Bông Bay", 215000, None, "phu_kien", "Cotton", "sp_mau_18.jpg"),
            ("Đầm Tiêu Y – Thạch", 465000, None, "dam", "Vải lanh", "sp_mau_19.jpg"),
            ("Áo khoác Tú Sam", 1275000, None, "ao", "Dạ pha", "sp_mau_20.jpg"),
            ("Quần Hạ Vân – Du", 875000, None, "vay", "Lụa pha", "sp_mau_21.jpg"),
            ("Áo khoác Đằng Sam", 985000, None, "ao", "Dạ", "sp_mau_22.jpg"),
            ("Ichiyu Dress", 725000, 975000, "dam", "Vải thô", "sp_mau_23.jpg"),
            ("Ichika Mesh Camisole", 275000, None, "ao", "Mesh", "sp_mau_24.jpg"),
            ("Ichika Mesh Top", 375000, None, "ao", "Mesh", "sp_mau_25.jpg"),
            ("Sonoko Blouse", 725000, None, "ao", "Lụa pha", "sp_mau_26.jpg"),
            ("Amiru Skirt", 575000, None, "vay", "Vải thô", "sp_mau_27.jpg"),
            ("Áo Dài Mạn Hoa", 1250000, None, "ao", "Lụa", "sp_mau_28.jpg"),
            ("Quần Tiêu Nhi", 198000, 395000, "vay", "Cotton", "sp_mau_29.jpg"),
            ("Quần Hoa Phong – Cúc", 500000, 625000, "vay", "Cotton pha", "sp_mau_30.jpg"),
            ("Áo khoác Kim Lĩnh", 920000, 1150000, "ao", "Dạ", "sp_mau_31.jpg"),
            ("Miki Striped Short", 98000, 245000, "vay", "Cotton", "sp_mau_32.jpg"),
            ("Áo Dài Minh Du", 1295000, None, "ao", "Lụa gấm", "sp_mau_33.jpg"),
            ("Đầm Tiêu Y", 465000, None, "dam", "Vải lanh", "sp_mau_34.jpg"),
        ]
        for ten, gia, gia_goc, dm, cl, anh in DS_SP:
            db.session.add(SanPham(
                nguoi_ban_id=admin.id, ten=ten, gia=gia, gia_goc=gia_goc,
                danh_muc=dm, chat_lieu=cl, anh=anh, kich_co='S,M,L,XL',
                mau_sac='', mo_ta='', so_luong=25, dang_ban=True))
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
