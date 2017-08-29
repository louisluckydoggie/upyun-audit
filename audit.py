# -*- encoding: utf8 -*-

import json
import MySQLdb
import html2text
import requests
import base64
import sys
import datetime
reload(sys)
sys.setdefaultencoding('utf8')

#请求数据库
db = MySQLdb.connect('10.0.6.60', 'techs_platform', 'techs_platform', 'techs_platform')
cur = db.cursor()
#cur.execute("SELECT * FROM review_domain where if_review = 0")
cur.execute("SELECT * FROM review_domain where domain_name = 'lalilali.com'")

for row in cur.fetchall():
    print row[0]
    h = html2text.HTML2Text()
    # Ignore converting links from HTML
    h.ignore_links = True

    #访问绑定域名，若出现超时、多次跳转或其他非预期响应，将错误记录在 requesterror.log；并且将域名标记为已审核
    try:
        update = db.cursor()
        r = requests.get('http://' + str(row[0]), timeout=10)
        update.execute("UPDATE review_domain SET if_review = 1 where domain_name = '" + row[0] + "'")
        db.commit()
    except requests.exceptions.Timeout as e:
        with open("requesterror.log", "a") as text_file:
            text_file.write("Timeout: %s %s\n" % (e, str(datetime.datetime.now())))
        update.execute("UPDATE review_domain SET if_review = 1 where domain_name = '" + row[0] + "'")
        db.commit()
        continue
    except requests.exceptions.TooManyRedirects as e:
        with open("requesterror.log", "a") as text_file:
            text_file.write("Too many redirects: %s %s\n" % (e, str(datetime.datetime.now())))
        update.execute("UPDATE review_domain SET if_review = 1 where domain_name = '" + row[0] + "'")
        db.commit()
        continue
    except requests.exceptions.RequestException as e:
        with open("requesterror.log", "a") as text_file:
            text_file.write("other error: %s %s\n" % (e, str(datetime.datetime.now())))
        update.execute("UPDATE review_domain SET if_review = 1 where domain_name = '" + row[0] + "'")
        db.commit()
        continue

    #HTML 转换成 TEXT
    r.encoding = 'UTF-8'
    audit_content = h.handle(r.text)

    #修复了接口返回 400 的错误，只检测前 400 个字符
    headers = {'Authorization': 'Basic ' + base64.b64encode('test:L12345678y')}
    body = {
        "text": str(audit_content).decode('utf-8')[:500]
    }
    body = json.dumps(body)

    # 文本长度超过 64KB 分成两段处理
    '''
    if len(body) > 65536:
        print '1'
        body1 = {
            "text": str(audit_content)[:(len(audit_content)/2)]
        }
        body2 = {
            "text": str(audit_content)[(len(audit_content)/2):]
        }
        body1 = json.dumps(body1)
        body2 = json.dumps(body2)
        print len(audit_content)/2
        print len(body1)
        print len(body2)
        try:
            result1 = requests.post('http://p1.api.upyun.com/louisserver/textaudit/detect', data=body1, headers=headers)
            result2 = requests.post('http://p1.api.upyun.com/louisserver/textaudit/detect', data=body2, headers=headers)
        except requests.exceptions.RequestException as e:
            with open("apierror.log", "a") as text_file:
                text_file.write("API return error: %s, Domain: %s %s\n" % e, str(row[0]), str(datetime.datetime.now()))
            continue

        if result1.status_code != 200:
            with open("apierror.log", "a") as text_file:
                text_file.write("API return1 error status: %s, Domain: %s %s\n" % (str(result1.status_code), str(row[0]),
                                str(datetime.datetime.now())))
            continue

        if result2.status_code != 200:
            with open("apierror.log", "a") as text_file:
                text_file.write("API return2 error status: %s, Domain: %s %s\n" % (str(result2.status_code), str(row[0]),
                                str(datetime.datetime.now())))
            continue

        # 判断是否违规
        if '"label":1' in result1.text or '"label":1' in result2.text:
            update.execute("UPDATE review_domain SET if_danger= 1 where domain_name = '" + row[0] + "'")
            db.commit()
        continue
    '''
    # 文本长度超过 64KB，只请求前面 20000 的内容
    '''
        if len(body) > 65536:
        try:
            data = str(audit_content).decode('utf-8')[:20000]
            body = {
                "text": data
            }
            body = json.dumps(body)
            #print body
            #print len(str(audit_content).decode('utf-8')[:30000])
            #print len(body)
        except Exception as e:
            with open("spliterror.log", "a") as text_file:
                text_file.write("error : %e, Domain: %s %s\n" % (e, str(row[0]),
                                                                 str(datetime.datetime.now())))
    '''

    #未超过 64KB，全部请求
    try:
        result = requests.post('http://p1.api.upyun.com/louisserver/textaudit/detect', data=body, headers=headers)
    except requests.exceptions.RequestException as e:
        with open("apierror.log", "a") as text_file:
            text_file.write("API return error: %s, Domain: %s %s\n" % (e, str(row[0]), str(datetime.datetime.now())))
        continue

    if result.status_code != 200:
        with open("apierror.log", "a") as text_file:
            text_file.write("API return error : %s, Domain: %s %s\n" % (str(result.text), str(row[0]),
                                                                        str(datetime.datetime.now())))
        continue

    #判断是否违规
    if '"label":1' in result.text:
        update.execute("UPDATE review_domain SET if_danger= 1 where domain_name = '" + row[0] + "'")
        db.commit()
db.close()



