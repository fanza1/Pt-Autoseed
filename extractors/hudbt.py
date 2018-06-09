# ！/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright (c) 2017-2020 Rhilip <rhilipruan@gmail.com>

import re

from bs4 import BeautifulSoup

from extractors.base.nexusphp import NexusPHP
from utils.constants import ubb_clean, episode_eng2chs, html2ubb
from utils.load.handler import rootLogger as Logger


def title_clean(noext: str) -> str:
    noext = re.sub("H\.264", "H_264", noext)
    noext = re.sub("([25])\.1", r"\1_1", noext)
    noext = re.sub("\.", " ", noext)
    noext = re.sub("H_264", "H.264", noext)
    noext = re.sub("[25]_1", r"\1.1", noext)
    return noext


class HUDBT(NexusPHP):
    url_host = "https://hudbt.hust.edu.cn"
    db_column = "hudbt.hust.edu.cn"

    @staticmethod
    def torrent_upload_err_message(post_text) -> str:
        outer_bs = BeautifulSoup(post_text, "lxml")
        outer_tag = outer_bs.find("div", id="stderr")
        outer_message = outer_tag.get_text().replace("\n", "")
        return outer_message

    def torrent_clone(self, tid) -> dict:
        """
        Get the raw information about the clone torrent's depend on given id,
        and sort it into a dict which can be converted to the post tuple.

        :param tid: int, The clone torrent's id in this site
        :return: dict, The information dict about this clone torrent
        """
        return_dict = {}
        details_bs = self.page_torrent_detail(tid=tid, bs=True)

        if re.search("没有该ID的种子", str(details_bs)):
            Logger.error("Error,this torrent may not exist or ConnectError")
        else:  # 解析原种页面
            return_dict["clone_id"] = tid  # 传入引用种子号
            return_dict["name"] = details_bs.find("h1", id="page-title").text  # 标题
            return_dict["small_descr"] = details_bs.find("dt", text="副标题").next_sibling.text  # 副标题

            imdb_another = details_bs.find("a", href=re.compile("http://www.imdb.com/title/tt"))
            return_dict["url"] = imdb_another.text if imdb_another else ""  # IMDb

            for key_dict, key_search in [("type", "cat"), ("standard_sel", "standard")]:  # 类型, 质量
                temp_reg = re.compile("torrents.php\?{}=(\d+)".format(key_search))
                temp_tag = details_bs.find("a", href=temp_reg)
                return_dict[key_dict] = re.search(temp_reg, temp_tag["href"]).group(1)

            # 简介
            descr_html = str((details_bs.select("div#kdescr > div.bbcode") or "")[0])
            descr_ubb = html2ubb(descr_html)
            return_dict["descr"] = ubb_clean(descr_ubb)

        return return_dict

    def date_raw_update(self, torrent_name_search, raw_info: dict) -> dict:
        type_ = int(raw_info["type"])
        if type_ == 418:  # 欧美剧集
            torrent_raw_name = torrent_name_search.group("full_name")
            raw_info["name"] = title_clean(torrent_raw_name)
            season_episode_info = episode_eng2chs(torrent_name_search.group("episode"))
            raw_info["small_descr"] = re.sub(r"第.+([集季])", season_episode_info, raw_info["small_descr"])
        if type_ == 427:  # 连载动漫
            ep = torrent_name_search.group("episode")
            raw_info["name"] = re.sub("^\d{2,3}(?:\.5|[Vv]2)? (TV|BD|WEB|DVD)", "{} \g<1>".format(ep), raw_info["name"])
            raw_info["small_descr"] = re.sub("第[\d ]+?话", "第 {} 话".format(ep), raw_info["small_descr"])

        return raw_info

    def data_raw2tuple(self, torrent, raw_info: dict) -> tuple:
        return (
            ("dl-url", ''),  # 下载链接
            ("name", raw_info["name"]),  # 主标题
            ("small_descr", raw_info["small_descr"]),  # 副标题
            ("url", raw_info["url"]),  # IMDb链接
            ("nfo", ''),  # NFO文件
            ("descr", self.enhance_descr(torrent=torrent, info_dict=raw_info)),  # 简介
            ("type", raw_info["type"]),  # 类型
            ("data[Tcategory][Tcategory][]", ''),  # 分类
            ("standard_sel", raw_info["standard_sel"])  # 质量
        )