# -*- coding: utf-8 -*-
import schedule
import time
from selenium import webdriver
from selenium.webdriver import ActionChains
import  urllib2
from bs4 import BeautifulSoup
import requests
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
import threading

from util.str_util import print_msg, send_mail
from spider.taobao_climber import TaobaoClimber
from mail.mail_sender_browser import MailSenderBrowser
from mail.mail_sender import *
from __init__ import *

if __name__ == '__main__':
    # 0.从本地文件读取账户信息
    with open(account_info_file, 'r') as f:
        lines = [l.strip('\n') for l in f.readlines()]
    taobao_username = lines[0]
    taobao_password = lines[1]
    mail_username = lines[2]
    mail_password = lines[3]

    # 1.给相关对象传入账号密码
    climber = TaobaoClimber(taobao_username, taobao_password)
    sender = MailSender(mail_username, mail_authorization_code)
    sender_browser = MailSenderBrowser(mail_username, mail_password, mail_password2)

    # 2.实例化driver
    # driver = webdriver.Firefox()  # 将Firefox浏览器驱动放于python根目录下
    driver = webdriver.Chrome("D:\Python\chromedriver.exe")  # 将Chrome驱动放于python根目录下或者直接给出Chrome驱动路径
    action = ActionChains(driver)
    driver.maximize_window()  # 浏览器最大化
    driver.set_page_load_timeout(delay_wait)  # 设定页面加载限制时间
    TaobaoClimber.driver = MailSenderBrowser.driver = driver
    TaobaoClimber.action = MailSenderBrowser.action = action

    # 3.建立标签页
    ## 默认淘宝标签页
    driver.execute_script("window.open('')")
    ## 新建邮箱标签页
    driver.execute_script("window.open('')")

    # 正则：解析留言内容
    re_note = re.compile(
        ur"^留言:[\u3000\u0020]*([\w.-]+@[\w.-]+\.\w+)\s*$")  # 格式; 留言： +任意空格+邮箱

    # 休眠总时间
    sleep_total_time = 0
    # 存在未留言订单
    exists_no_note_order = False

    # 邮件固定格式
    ## 发给买家链接
    ### TODO 百度云链接以及密码（后续也可类似账户密码，通过读取配置文件得到链接密码）
    msgLink = MIMEText('链接: https://pan.baidu.com/s/19RMq7zBhVPXa4012GVhMaQ 提取码: 928b', 'plain', 'utf-8')
    ### TODO 淘宝店名
    msgLink['From'] = formataddr(["Seller", mail_username])  # 括号里的对应发件人邮箱昵称、发件人邮箱账号
    msgLink['Subject'] = "下载链接，请及时查收，无须回复；如链接失效，请在淘宝内联系卖家"  # 邮件的主题，也可以说是标题
    ## 提醒卖家发送失败
    msgFailure = MIMEText('存在订单发送邮件失败，请及时处理', 'plain', 'utf-8')
    msgFailure['From'] = formataddr(["Seller", mail_username])  # 括号里的对应发件人邮箱昵称、发件人邮箱账号
    # msgFailure['To'] = formataddr["Seller", mail_username]
    msgFailure['Subject'] = "存在订单发送邮件失败，请及时处理"  # 邮件的主题，也可以说是标题

    # 2.1上架宝贝
    # climber.shelve()
    is_running = True
    while is_running:
        localtime = time.asctime(time.localtime(time.time()))
        print localtime
        # 2.2爬取订单
        orders = climber.climb()
        orders_len = len(orders)
        for order in orders:
            if climber.deliver_judge(order[0]) is False:
                print "这个订单已经发货"
                continue
            note_array = re.findall(re_note, order[3])
            if len(note_array) != 1:
                if mail_notice_for_no_note:
                    exists_no_note_order = True
                continue
            my_user = note_array
            if mail_send_type == 2:
                ret = True
                try:
                    # TODO 买家昵称
                    msgLink['To'] = formataddr(["Purchaser", my_user])  # 括号里的对应收件人邮箱昵称、收件人邮箱账号

                    server = smtplib.SMTP_SSL("smtp.qq.com", 465)  # 发件人邮箱中的SMTP服务器，端口是25
                    server.login(mail_username, mail_password)  # 括号中对应的是发件人邮箱账号、邮箱密码
                    server.sendmail(mail_username, [my_user, ], msgLink.as_string())  # 括号中对应的是发件人邮箱账号、收件人邮箱账号、发送邮件
                    server.quit()  # 关闭连接
                except Exception:  # 如果 try 中的语句没有执行，则会执行下面的 ret=False
                    print "邮件发送失败"

                    # TODO 发送邮件提醒卖家
                    msgFailure['To'] = formataddr["Seller", mail_username]
                    server = smtplib.SMTP_SSL("smtp.qq.com", 465)  # 发件人邮箱中的SMTP服务器，端口是25
                    server.login(mail_username, mail_password)  # 括号中对应的是发件人邮箱账号、邮箱密码
                    server.sendmail(mail_username, [my_user, ], msgFailure.as_string())  # 括号中对应的是发件人邮箱账号、收件人邮箱账号、发送邮件
                    server.quit()  # 关闭连接

                    ret = False
                # 2.6 订单改为已发货
                if climber.delivered(order[0]) is True:
                    print "更改这个订单为已经发货"
                else:
                    print "更改该订单发货状态失败"
        time.sleep(60)
