FROM --platform=linux/amd64 python:3.9

RUN apt update

RUN apt-get install -y curl vim

# optional: for unixODBC development headers
RUN  apt-get install -y unixodbc-dev

# optional: kerberos library for debian-slim distributions
RUN  apt-get install -y libgssapi-krb5-2

CMD ["/bin/bash"]
