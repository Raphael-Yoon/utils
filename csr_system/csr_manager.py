from flask import Flask, render_template, request, redirect, url_for, flash
import database as db
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'antigravity_secret_key'

# 초기화: 테이블 생성
db.init_db()

@app.route('/')
def index():
    """메인 대시보드: 모든 SR 목록 조회"""
    conn = db.get_db_connection()
    requests = conn.execute('SELECT * FROM service_requests ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('index.html', requests=requests)

@app.route('/create', methods=['GET', 'POST'])
def create():
    """SR 생성"""
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        requester = request.form.get('requester')
        sr_id = db.generate_sr_id()
        
        conn = db.get_db_connection()
        conn.execute(
            'INSERT INTO service_requests (sr_id, title, content, requester) VALUES (?, ?, ?, ?)',
            (sr_id, title, content, requester)
        )
        conn.commit()
        conn.close()
        
        flash(f'서비스 요청 {sr_id}가 생성되었습니다.', 'success')
        return redirect(url_for('index'))
    
    return render_template('create.html')

@app.route('/detail/<int:id>')
def detail(id):
    """SR 상세 보기"""
    conn = db.get_db_connection()
    sr = conn.execute('SELECT * FROM service_requests WHERE id = ?', (id,)).fetchone()
    conn.close()
    if sr is None:
        return "Not Found", 404
    return render_template('detail.html', sr=sr)

@app.route('/approve/<int:id>', methods=['POST'])
def approve(id):
    """승인 처리 및 증빙 로그 기록"""
    approver = request.form.get('approver', 'Raphael')
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log = f"SUCCESS: APPROVED BY {approver} AT {now}"
    
    conn = db.get_db_connection()
    conn.execute(
        'UPDATE service_requests SET status = ?, approved_at = ?, approver = ?, evidence_log = ? WHERE id = ?',
        ('Approved', now, approver, log, id)
    )
    conn.commit()
    conn.close()
    
    flash(f'승인이 완료되었습니다.', 'success')
    return redirect(url_for('detail', id=id))

@app.route('/reject/<int:id>', methods=['POST'])
def reject(id):
    """거절 처리"""
    approver = request.form.get('approver', 'Raphael')
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log = f"REJECTED BY {approver} AT {now}"
    
    conn = db.get_db_connection()
    conn.execute(
        'UPDATE service_requests SET status = ?, approved_at = ?, approver = ?, evidence_log = ? WHERE id = ?',
        ('Rejected', now, approver, log, id)
    )
    conn.commit()
    conn.close()
    
    flash(f'요청이 거절되었습니다.', 'danger')
    return redirect(url_for('detail', id=id))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
