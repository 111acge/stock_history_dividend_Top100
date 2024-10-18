import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
import akshare as ak
import pandas as pd

# 创建一个文件夹来存储所有的HTML文件
output_folder = "dividend_reports"
os.makedirs(output_folder, exist_ok=True)


@lru_cache(maxsize=None)
def get_stock_dividend_cninfo(symbol):
    try:
        return ak.stock_dividend_cninfo(symbol=symbol)
    except Exception as e:
        return pd.DataFrame()


def process_company(row, stock_prices):
    code = format_code(row['代码'])
    company_file = f"{code}.html"
    latest_price = stock_prices.get(code, "N/A")

    stock_dividend_cninfo_df = get_stock_dividend_cninfo(code)
    detailed_info = stock_dividend_cninfo_df.to_html(
        index=False) if not stock_dividend_cninfo_df.empty else f"<p>无法获取详细信息</p>"

    company_html = f"""
    <html>
    <head>
        <title>{row['名称']} ({code}) 分红详情</title>
        <style>
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid black; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <h1>{row['名称']} ({code}) 分红详情</h1>
        <p>最新股价: {latest_price}</p>
        {detailed_info}
        <p><a href="index.html">返回主页</a></p>
    </body>
    </html>
    """

    with open(os.path.join(output_folder, company_file), 'w', encoding='utf-8') as f:
        f.write(company_html)

    return f"""
        <tr>
            <td><a href="{company_file}">{code}</a></td>
            <td>{row['名称']}</td>
            <td>{row['上市日期'].strftime('%Y-%m-%d')}</td>
            <td>{latest_price}</td>
            <td>{row['累计股息']:.4f}</td>
            <td>{row['年均股息']:.4f}</td>
            <td>{row['分红次数']}</td>
            <td>{row['融资总额']:.4f}</td>
            <td>{row['融资次数']}</td>
        </tr>
    """


def format_code(x):
    return str(x).zfill(6)


def main():
    # 获取分红数据
    stock_history_dividend_df = ak.stock_history_dividend()

    # 按累计股息降序排序并只保留前100家公司
    top_dividend = stock_history_dividend_df.nlargest(100, '累计股息')

    # 获取最新A股行情数据
    stock_zh_a_spot_em_df = ak.stock_zh_a_spot_em()

    # 创建一个字典，用于快速查找股票价格
    stock_prices = dict(zip(stock_zh_a_spot_em_df['代码'], stock_zh_a_spot_em_df['最新价']))

    # 读取 HTML 模板
    with open('index_template.html', 'r', encoding='utf-8') as f:
        html_template = f.read()

    # 使用多线程处理公司数据
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_row = {executor.submit(process_company, row, stock_prices): row for _, row in top_dividend.iterrows()}
        table_rows = []
        for future in as_completed(future_to_row):
            table_rows.append(future.result())

    # 将表格数据插入到 HTML 模板中
    main_html = html_template.replace('<!-- 表格数据将通过 Python 脚本动态生成 -->', ''.join(table_rows))

    # 保存主页面
    with open(os.path.join(output_folder, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(main_html)

    print(f"所有报告已生成在 '{output_folder}' 文件夹中。")
    print(f"请打开 '{os.path.join(output_folder, 'index.html')}' 查看主页面。")


if __name__ == "__main__":
    main()
