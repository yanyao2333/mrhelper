FROM python:3.9 as requirements-stage

WORKDIR /tmp

COPY ./pyproject.toml ./poetry.lock* /tmp/

ENV PATH="${PATH}:/root/.local/bin"

RUN curl -sSL https://install.python-poetry.org -o install-poetry.py  \
    && python install-poetry.py --yes  \
    && poetry export -f requirements.txt --output requirements.txt --without-hashes

FROM tiangolo/uvicorn-gunicorn-fastapi:python3.9

WORKDIR /app

COPY --from=requirements-stage /tmp/requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade -r requirements.txt  \
    && rm requirements.txt

CMD cd /app  \
    && echo "############################开始从yanyao233/mrhelper下载最新的版本##########################"  \
    && if [ -f ".env" ]; then cp ./.env /tmp; fi  \
    && if [ -f "./src/plugins/nonebot_plugin_mrhelper/mrhelper.db" ]; then cp ./src/plugins/nonebot_plugin_mrhelper/mrhelper.db /tmp; fi  \
    && if [ -d "./accounts" ]; then cp -r ./accounts /tmp; fi  \
    && rm -rf ./*  \
    && wget https://ghproxy.com/https://github.com/yanyao2333/mrhelper/archive/refs/heads/main.zip  \
    && unzip ./main.zip  \
    && cp -r ./mrhelper-main/. ./  \
    && rm -rf ./main.zip ./mrhelper-main  \
    && if [ -f "/tmp/.env" ]; then mv /tmp/.env ./; fi  \
    && if [ -f "/tmp/mrhelper.db" ]; then mv /tmp/mrhelper.db ./src/plugins/nonebot_plugin_mrhelper/; fi  \
    && if [ -d "/tmp/accounts" ]; then mv /tmp/accounts ./; fi  \
    && echo "##########################下载更新完成 开始启动nonebot2############################"  \
    && nb run