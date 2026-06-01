from flask import Flask, render_template, request, redirect, url_for, jsonify
import pandas as pd
import os
from datetime import datetime
import zoneinfo
import threading

def get_beijing_time():
    """获取北京时间"""
    return datetime.now(zoneinfo.ZoneInfo("Asia/Shanghai"))

app = Flask(__name__)
DATA_DIR = '/app/data'
os.makedirs(DATA_DIR, exist_ok=True)
EXCEL_FILE = os.path.join(DATA_DIR, 'movies_data.xlsx')
data_lock = threading.Lock()

# 版本号
VERSION = "1.0.0"
try:
    with open('VERSION', 'r') as f:
        VERSION = f.read().strip()
except:
    pass

def load_movies():
    if os.path.exists(EXCEL_FILE):
        return pd.read_excel(EXCEL_FILE)
    else:
        df = pd.DataFrame(columns=['序号', '页码', '电影名', '磁力链接', '保存时间'])
        df.to_excel(EXCEL_FILE, index=False)
        return df

def save_movies(df):
    df.to_excel(EXCEL_FILE, index=False)

def build_movie_list(df):
    movies = []
    for _, row in df.iterrows():
        magnet = row['磁力链接']
        if pd.isna(magnet) or str(magnet).strip() == '':
            magnet_display = '(空)'
            magnet = ''
            is_empty = True
        else:
            magnet = str(magnet)
            magnet_display = magnet[:50] + '...' if len(magnet) > 50 else magnet
            is_empty = False
        
        movies.append({
            'id': row['序号'],
            'page': row['页码'],
            'name': str(row['电影名']) if not pd.isna(row['电影名']) else '',
            'magnet': magnet,
            'magnet_display': magnet_display,
            'is_empty': is_empty,
            'save_time': row['保存时间']
        })
    return movies

@app.route('/')
def index():
    page_num = request.args.get('page', 1)
    try:
        page_num = int(page_num)
    except ValueError:
        page_num = 1
    
    try:
        with data_lock:
            df = load_movies()
        
        if df.empty:
            return render_template('index.html', movies=[], current_page=0, all_page_nums=[], version=VERSION)
        
        all_page_nums = sorted(df['页码'].unique(), reverse=True)
        
        if page_num not in all_page_nums:
            if all_page_nums:
                page_num = all_page_nums[0]
            else:
                page_num = 0
        
        page_df = df[df['页码'] == page_num]
        movies = build_movie_list(page_df)
        
        return render_template('index.html', 
                              movies=movies, 
                              current_page=page_num, 
                              all_page_nums=all_page_nums,
                              version=VERSION)
    except Exception as e:
        return render_template('index.html', movies=[], current_page=0, all_page_nums=[], version=VERSION,
                              error=f'加载数据失败: {str(e)}')

@app.route('/search')
def search():
    keyword = request.args.get('keyword', '')
    
    try:
        with data_lock:
            df = load_movies()
        
        if not keyword or df.empty:
            return redirect(url_for('index'))
        
        mask = df['电影名'].str.lower().str.contains(keyword.lower(), na=False)
        result_df = df[mask]
        movies = build_movie_list(result_df)
        
        return render_template('search.html', movies=movies, keyword=keyword, version=VERSION)
    except Exception as e:
        return redirect(url_for('index'))

@app.route('/add', methods=['POST'])
def add_movie():
    page = request.form.get('page')
    name = request.form.get('name')
    magnet = request.form.get('magnet', '')
    
    if not page or not name:
        return jsonify({'success': False, 'message': '页码和电影名不能为空'})
    
    try:
        page = int(page)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': '页码必须是数字'})
    
    try:
        with data_lock:
            df = load_movies()
            
            new_id = len(df) + 1
            new_movie = {
                '序号': new_id,
                '页码': page,
                '电影名': name,
                '磁力链接': magnet,
                '保存时间': get_beijing_time().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            df = pd.concat([df, pd.DataFrame([new_movie])], ignore_index=True)
            save_movies(df)
        
        return jsonify({'success': True, 'message': '添加成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'添加失败: {str(e)}'})

@app.route('/delete/<int:movie_id>', methods=['POST'])
def delete_movie(movie_id):
    try:
        with data_lock:
            df = load_movies()
            
            if movie_id not in df['序号'].values:
                return jsonify({'success': False, 'message': '电影记录不存在'})
            
            df = df[df['序号'] != movie_id]
            df['序号'] = range(1, len(df) + 1)
            save_movies(df)
        
        return jsonify({'success': True, 'message': '删除成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})

@app.route('/update/<int:movie_id>', methods=['POST'])
def update_movie(movie_id):
    page = request.form.get('page', '').strip()
    name = request.form.get('name', '').strip()
    magnet = request.form.get('magnet', '').strip()
    
    try:
        with data_lock:
            df = load_movies()
            
            if movie_id not in df['序号'].values:
                return jsonify({'success': False, 'message': '电影记录不存在'})
            
            if page:
                try:
                    df.loc[df['序号'] == movie_id, '页码'] = int(page)
                except (ValueError, TypeError):
                    return jsonify({'success': False, 'message': '页码必须是数字'})
            if name:
                df.loc[df['序号'] == movie_id, '电影名'] = name
            if magnet:
                df.loc[df['序号'] == movie_id, '磁力链接'] = magnet
            df.loc[df['序号'] == movie_id, '保存时间'] = get_beijing_time().strftime('%Y-%m-%d %H:%M:%S')
            
            save_movies(df)
        
        return jsonify({'success': True, 'message': '更新成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})

@app.route('/reorder', methods=['POST'])
def reorder_movies():
    order = request.form.get('order', '')
    
    if not order:
        return jsonify({'success': False, 'message': '排序数据为空'})
    
    try:
        id_list = [int(x) for x in order.split(',')]
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': '排序数据格式错误'})
    
    try:
        with data_lock:
            df = load_movies()
            
            if df.empty:
                return jsonify({'success': False, 'message': '没有电影数据'})
            
            if len(id_list) != len(df):
                return jsonify({'success': False, 'message': '排序数据数量不匹配'})
            
            new_df = pd.DataFrame()
            for idx, movie_id in enumerate(id_list, 1):
                row = df[df['序号'] == movie_id]
                if row.empty:
                    return jsonify({'success': False, 'message': f'电影记录 {movie_id} 不存在'})
                row = row.copy()
                row['序号'] = idx
                new_df = pd.concat([new_df, row], ignore_index=True)
            
            save_movies(new_df)
        
        return jsonify({'success': True, 'message': '排序已保存'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'排序失败: {str(e)}'})

@app.route('/copy_magnet/<int:movie_id>')
def copy_magnet(movie_id):
    try:
        with data_lock:
            df = load_movies()
        
        row = df[df['序号'] == movie_id]
        
        if not row.empty:
            magnet = row.iloc[0]['磁力链接']
            if not pd.isna(magnet) and str(magnet).strip() != '':
                return jsonify({'success': True, 'magnet': str(magnet)})
        
        return jsonify({'success': False, 'message': '磁力链接为空'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取失败: {str(e)}'})

if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug)
