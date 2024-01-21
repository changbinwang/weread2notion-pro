import argparse
import json
import logging
import os
import re
import time
from notion_client import Client
import requests

from datetime import datetime, timedelta
import hashlib
from notion_helper import NotionHelper
from weread_api import WeReadApi

from utils import (
    format_date,
    format_time,
    get_callout,
    get_date,
    get_file,
    get_heading,
    get_icon,
    get_number,
    get_number_from_result,
    get_quote,
    get_relation,
    get_rich_text,
    get_rich_text_from_result,
    get_table_of_contents,
    get_title,
    get_url,
)


TAG_ICON_URL = "https://www.notion.so/icons/tag_gray.svg"
USER_ICON_URL = "https://www.notion.so/icons/user-circle-filled_gray.svg"
TARGET_ICON_URL = "https://www.notion.so/icons/target_red.svg"
BOOKMARK_ICON_URL = "https://www.notion.so/icons/bookmark_gray.svg"








def download_image(url, save_dir="cover"):
    # 确保目录存在，如果不存在则创建
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # 获取文件名，使用 URL 最后一个 '/' 之后的字符串
    file_name = url.split("/")[-1] + ".jpg"
    save_path = os.path.join(save_dir, file_name)

    # 检查文件是否已经存在，如果存在则不进行下载
    if os.path.exists(save_path):
        print(f"File {file_name} already exists. Skipping download.")
        return save_path

    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(save_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=128):
                file.write(chunk)
        print(f"Image downloaded successfully to {save_path}")
    else:
        print(f"Failed to download image. Status code: {response.status_code}")
    return save_path


def create_highlight_with_auto_retry(token, highlight_data, max_retries=5, retry_interval=60):
    url = "https://readwise.io/api/v2/highlights/"
    headers = {"Authorization": f"Token {token}"}
    retries = 0

    while retries < max_retries:
        try:
            response = requests.post(url, headers=headers, json=highlight_data)
            response.raise_for_status()  # 触发异常以处理非成功状态码
            return response.json()  # 成功创建高亮
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                # 当达到速率限制时，API 会返回 429 错误
                retry_after = int(e.response.headers.get("Retry-After", retry_interval))
                print(f"速率限制达到，将在 {retry_after} 秒后重试")
                time.sleep(retry_after)
                retries += 1  # 增加重试计数
            else:
                # 非速率限制的其他错误
                print(f"请求失败，状态码：{e.response.status_code}")
                break
    return None




if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    options = parser.parse_args()
    weread_cookie = os.getenv("WEREAD_COOKIE")
    readwise_token = os.getenv("READWISE_TOKEN")
    branch = os.getenv("REF").split("/")[-1]
    repository =  os.getenv("REPOSITORY")
    weread_api = WeReadApi()
    books = weread_api.get_notebooklist()
    if books != None:
        for index, book in enumerate(books):
            sort = book.get("sort")
            book = book.get("book")
            title = book.get("title")
            cover = book.get("cover")
            if book.get("author") == "公众号" and book.get("cover").endswith("/0"):
                cover += ".jpg"
            if cover.startswith("http") and not cover.endswith(".jpg"):
                path = download_image(cover)
                cover = (
                    f"https://raw.githubusercontent.com/{repository}/{branch}/{path}"
                )
            bookId = book.get("bookId")
            author = book.get("author")
            categories = book.get("categories")
            if categories != None:
                categories = [x["title"] for x in categories]
            print(f"正在同步《{title}》,一共{len(books)}本，当前是第{index+1}本。")
            bookmarks = weread_api.get_bookmark_list(bookId)
            for i in bookmarks:
                highlighted_at_time = datetime.utcfromtimestamp(i.get("createTime"))
                json={
                    "highlights": [{
                        "text": i.get("markText"),
                        "title": title,
                        "author": author,
                        "image_url": cover,
                        "source_type": "weread",
                        "category": "books",
                        }]
                    }
                print(json)
                create_highlight_with_auto_retry(readwise_token,json)