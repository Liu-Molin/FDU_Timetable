# !/usr/bin/env python
# --------------------------------------------------------------
# File:          fetchdata.py
# Project:       FDU_Timetable
# Created:       Tuesday, 12th November 2019 2:36:48 pm
# @Author:       Molin Liu, MSc in Data Science
# Contact:          molin@live.cn
# Last Modified: Tuesday, 12th November 2019 2:36:58 pm
# Copyright  © Rockface 2019 - 2020
# --------------------------------------------------------------

import requests
import time
import datetime
import pytz
import os
import re
from fdulogin import FDU_User
import autologin
from bs4 import BeautifulSoup
from FDU_headers import HEADER_CAPTCHA, HEADER_LOGIN, HEADER_LT
from utils import parseCookie, saveHtml
import fileman


class Course():
    def __init__(self):
        self.__teacher_id = []
        self.teacher_names = []
        self.__course_id = ""
        self.course_name = ""
        self.__room_id = ""
        self.room_name = ""
        self.available_week = []
        self.course_time = set()

    def __repr__(self):
        temp_str = self.course_name+',' + \
            self.__room_id+',\t'+(', '.join(self.course_time))
        return temp_str

    def __str__(self):
        temp_str = self.course_name+','+self.__room_id + \
            ',\t'+(', '.join(self.course_time))+',\t' + \
            (', '.join(str(i) for i in self.available_week))
        return temp_str

    def __hash__(self):
        return hash(self.__course_id)

    def __eq__(self, other):
        return other.getID() == self.__course_id

    def _readWeek(self, week):
        self.available_week = [i.start() for i in re.finditer('1', week)]

    def getID(self):
        return self.__course_id

    def readStr(self, course_info, course_time):
        course_info = course_info.strip('"').split('","')
        teachers = course_info[0].split(',')
        for i in teachers:
            self.__teacher_id.append(i)

        teachers_name = course_info[1].split(',')
        for i in teachers_name:
            self.teacher_names.append(i)
        self.__course_id = course_info[2]
        self.course_name = course_info[3]
        self.__room_id = course_info[4]
        self.room_name = course_info[5]
        self._readWeek(course_info[6])
        for i in range(len(course_time)):
            temp_string = course_time[i].replace('*unitCount+', ',')
            self.course_time.add(temp_string)


class TableManager():

    def __init__(self, session, cookies):
        self.__session = session
        self.__cookies = cookies
        self.__query_form = {}

        self.course_list = []

    def _parse_course(self, info):
        new_course = Course()
        course_info = re.search(r'[\t]*activity = .*;', info).group(0)
        course_info = re.search(r'\(.*\)', course_info).group(0).strip('()')
        course_time = re.findall(r'.\*unitCount\+.', info)

        new_course.readStr(course_info, course_time)
        self.course_list.append(new_course)

    def data_clean(self, resp):
        parsed_text = BeautifulSoup(resp.text, 'lxml')
        courses = parsed_text.find_all('script')
        courses = re.findall(
            r"(\t*activity = new.*\n(\t*index =.*\n\t*table0.*\n)*)", str(courses))
        # print(courses)
        #courses = re.findall(r'[\t]*activity = .*;', str(courses))
        for i in courses:
            self._parse_course(str(i))

    def fetchTablePage(self):
        '''
        Get table page
        '''
        header = HEADER_LOGIN
        get_url = "http://jwfw.fudan.edu.cn/eams/courseTableForStd.action"

        resp = self.__session.get(
            get_url, headers=header, cookies=self.__cookies)
        self._set_cookies(resp)
        print(resp)
        self._get_ids(resp)
        saveHtml("TablePage", resp.text, resp.status_code)
        # print(self.__session.cookies)

    def getTable(self):
        post_url = "http://jwfw.fudan.edu.cn/eams/courseTableForStd!courseTable.action"
        post_form = {
            "ignoreHead": "1",
            "setting.kind": "std",
            "startWeek": "1",
            "semester.id": self.__session.cookies['semester.id']
        }
        post_form.update(self.__query_form)

        resp = self.__session.post(post_url, data=post_form, headers=HEADER_LOGIN,
                                   cookies=self.__cookies, timeout=40, allow_redirects=False)
        print(resp)
        saveHtml("Table", resp.text, resp.status_code)
        return resp

    def _set_cookies(self, resp):
        '''
        Set cookies from response
        '''
        has_cookies = resp.cookies.get_dict()
        self.__cookies.update(has_cookies)
        set_cookies = parseCookie(resp.headers['Set-Cookie'])
        print(has_cookies)
        print(set_cookies)
        self.__cookies.update(set_cookies)

    def _get_ids(self, resp):
        '''
        Get ids for form posting.
        '''
        parsed_text = BeautifulSoup(resp.text, 'lxml')
        ids = parsed_text.find_all('script')
        ids = re.search(r'"ids","[0-9]*"', str(ids)).group(0)
        ids = re.sub('"', '', ids).split(',')
        self.__query_form['ids'] = ids[1]


def processing(session, cookies):
    tm = TableManager(session, cookies)
    tm.fetchTablePage()
    resp_table = tm.getTable()
    tm.data_clean(resp_table)
    print(tm.course_list)
    fileman.createCalendar(tm.course_list)


if __name__ == "__main__":
    user = FDU_User(autologin.id(), autologin.pw())
    session, cookies = user.finish_login()

    processing(session, cookies)
