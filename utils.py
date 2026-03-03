# utils.py （内容与之前基本相同，这里只贴变化部分）
def load_and_split_docs(data_dir="data"):
    if not os.path.exists(data_dir):
        raise FileNotFoundError(f"制度文档目录 {data_dir} 不存在")
    # ... 其余代码不变
