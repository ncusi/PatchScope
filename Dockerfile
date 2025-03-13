# syntax=docker/dockerfile:1
FROM python:3.11

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
RUN python3 -m pip install --no-cache-dir --upgrade pip
RUN python3 -m pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY . .
RUN python3 -m pip install --no-cache-dir --upgrade .[web]

EXPOSE 7860
CMD ["panel", "serve", \
     "/code/src/diffinsights_web/apps/contributors.py", \
     "/code/src/diffinsights_web/apps/author.py", \
     "--index=contributors", \
     "--reuse-sessions", "--global-loading-spinner", \
     "--address", "0.0.0.0", "--port", "7860",  \
     "--allow-websocket-origin", "*" \
]

RUN mkdir /.cache
RUN chmod 777 /.cache
RUN mkdir .chroma
RUN chmod 777 .chroma
