import datetime
import sqlite3

from nonebot.log import logger

class DB:
    WORK_DIR = ""

    def __init__(self, WORK_DIR):
        logger.info(f"数据库目录：{WORK_DIR}")
        DB.WORK_DIR = WORK_DIR
        self.Start()
        self.CreatTable()
        self.Close()
        logger.success("数据库初始化成功！")
        # print(self.id)

    def Start(self):
        self.conn = sqlite3.connect(DB.WORK_DIR)
        self.cursor = self.conn.cursor()

    def CreatTable(self):
        try:
            sql = '''
            CREATE TABLE IF NOT EXISTS `users`(
               `id` INTEGER PRIMARY KEY,
               `qid` INT NOT NULL,
               `username` NOT NULL,
               `password` NOT NULL,
               `token` NOT NULL,
               `admin` INT NOT NULL,
               `update_date` NOT NULL 
            );
            '''
            self.cursor.execute(sql)
            return 1
        except Exception as e:
            logger.error(f"Creat Error:{e}")
            return 0

    def Insert(self, qid: int, username, password, token, admin: int):
        try:
            sql = '''
            INSERT INTO users ( id, qid, username, password, token, admin, update_date )
            VALUES
            (NULL, ?, ?, ?, ?, ?, ?);
           '''
            self.Start()
            self.cursor.execute(sql, (qid, username, password, token, admin, datetime.datetime.today()))
            self.conn.commit()
            self.Close()
            return 1
        except Exception as e:
            logger.error(f"Creat Error:{e}")
            return 0

    def Select(self, list, key):
        self.Start()
        self.cursor.execute(f'''SELECT * from users WHERE {list} = {key} order by id desc;''')
        res = self.cursor.fetchone()
        self.Close()
        return res

    # 刷新token的sql操作函数
    def UpdateToken(self, id, token):
        self.Start()
        self.cursor.execute(f"""UPDATE users SET token = "{token}" WHERE id = {id};""")
        today = datetime.datetime.today()
        self.cursor.execute(f"""UPDATE users SET update_date = "{today}" WHERE id = {id};""")
        self.conn.commit()
        self.Close()

    def Count(self):
        self.Start()
        self.cursor.execute("select * from users")
        results = self.cursor.fetchall()
        results = len(results)
        self.Close()
        return results

    def Close(self):
        self.cursor.close()
        self.conn.close()
