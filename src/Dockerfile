FROM python:3.8

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV TZ="Europe/Rome"

RUN apt-get -q -y update && \
    apt-get -q -y upgrade && \
    apt-get install -y -q --no-install-recommends \
        build-essential \
        libpcre3-dev \
        libpq-dev \
        postgresql-client


RUN mkdir /usr/src/Core
WORKDIR /usr/src/Core

RUN pip install --upgrade pip

COPY . /usr/src/Core/

RUN pip install -r requirements.txt

#EXPOSE 8000

#CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

RUN python manage.py collectstatic

#RUN chmod +x /usr/src/Core/wait_for_db.sh
#ENTRYPOINT ["/usr/src/Core/wait_for_db.sh"]

#chmod +x src/wait_for_db.sh