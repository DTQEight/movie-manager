from flask import Flask, render_template, request, redirect, url_for, jsonify
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)
DATA_DIR = '/app/data'
os.makedirs(DATA_DIR, exist_ok=True)
EXCEL_FILE = os.path.join(DATA_DIR, 'movies_data.xlsx')

def load_movies():
    if os.path.exists(EXCEL_FILE):
        return pd.read_excel(EXCEL_FILE)
    else:
        df = pd.DataFrame(columns=['序号', '页码', '电影名', '磁力链接', '保存时间'])
        df.to_excel(EXCEL_FILE, index=False)
        return df

def save_movies(df):
    df.to_excel(EXCEL_FILE, index=False)

@app.route('/')
def index():
    page_num = request.args.get('page', 1)
    try:
        page_num = int(page_num)
    except ValueError:
        page_num = 1
    
    df = load_movies()
    
    if df.empty:
        return render_template('index.html', movies=[], current_page=0, total_pages=0)
    
    all_page_nums = sorted(df['页码'].unique(), reverse=True)
    
    if page_num not in all_page_nums:
        if all_page_nums:
            page_num = all_page_nums[0]
        else:
            page_num = 0
    
    page_df = df[df['页码'] == page_num]
    
    movies = []
    for _, row in page_df.iterrows():
        magnet = row['磁力链接']
        if pd.isna(magnet) or str(magnet).strip() == '':
            magnet_display = '(空)'
            is_empty = True
        else:
            magnet_display = magnet[:50] + '...' if len(str(magnet)) > 50 else magnet
            is_empty = False
        
        movies.append({
            'id': row['序号'],
            'page': row['页码'],
            'name': row['电影名'],
            'magnet': row['磁力链接'],
            'magnet_display': magnet_display,
            'is_empty': is_empty,
            'save_time': row['保存时间']
        })
    
    return render_template('index.html', 
                          movies=movies, 
                          current_page=page_num, 
                          all_page_nums=all_page_nums)

@app.route('/search')
def search():
    keyword = request.args.get('keyword', '')
    df = load_movies()
    
    if not keyword or df.empty:
        return redirect(url_for('index'))
    
    mask = df['电影名'].str.lower().str.contains(keyword.lower(), na=False)
    result_df = df[mask]
    
    movies = []
    for _, row in result_df.iterrows():
        magnet = row['磁力链接']
        if pd.isna(magnet) or str(magnet).strip() == '':
            magnet_display = '(空)'
            is_empty = True
        else:
            magnet_display = magnet[:50] + '...' if len(str(magnet)) > 50 else magnet
            is_empty = False
        
        movies.append({
            'id': row['序号'],
            'page': row['页码'],
            'name': row['电影名'],
            'magnet': row['磁力链接'],
            'magnet_display': magnet_display,
            'is_empty': is_empty,
            'save_time': row['保存时间']
        })
    
    return render_template('search.html', movies=movies, keyword=keyword)

@app.route('/add', methods=['POST'])
def add_movie():
    page = request.form.get('page')
    name = request.form.get('name')
    magnet = request.form.get('magnet', '')
    
    if not page or not name:
        return jsonify({'success': False, 'message': '页码和电影名不能为空'})
    
    df = load_movies()
    
    new_id = len(df) + 1
    new_movie = {
        '序号': new_id,
        '页码': int(page),
        '电影名': name,
        '磁力链接': magnet,
        '保存时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    df = df.append(new_movie, ignore_index=True)
    save_movies(df)
    
    return jsonify({'success': True, 'message': '添加成功'})

@app.route('/delete/<int:movie_id>', methods=['POST'])
def delete_movie(movie_id):
    df = load_movies()
    df = df[df['序号'] != movie_id]
    
    df['序号'] = range(1, len(df) + 1)
    save_movies(df)
    
    return jsonify({'success': True, 'message': '删除成功'})

@app.route('/update/<int:movie_id>', methods=['POST'])
def update_movie(movie_id):
    page = request.form.get('page', '').strip()
    name = request.form.get('name', '').strip()
    magnet = request.form.get('magnet', '').strip()
    
    df = load_movies()
    
    if page:
        df.loc[df['序号'] == movie_id, '页码'] = int(page)
    if name:
        df.loc[df['序号'] == movie_id, '电影名'] = name
    if magnet:
        df.loc[df['序号'] == movie_id, '磁力链接'] = magnet
    df.loc[df['序号'] == movie_id, '保存时间'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    save_movies(df)
    
    return jsonify({'success': True, 'message': '更新成功'})

@app.route('/copy_magnet/<int:movie_id>')
def copy_magnet(movie_id):
    df = load_movies()
    row = df[df['序号'] == movie_id]
    
    if not row.empty:
        magnet = row.iloc[0]['磁力链接']
        if not pd.isna(magnet) and str(magnet).strip() != '':
            return jsonify({'success': True, 'magnet': str(magnet)})
    
    return jsonify({'success': False, 'message': '磁力链接为空'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
