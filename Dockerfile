# Use an official Python runtime as a parent image
FROM python:3.9-alpine

ENV TZ=Asia/Shanghai

RUN apk update && apk add tzdata

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo > /etc/timezone

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the current directory contents into the container at /usr/src/app
COPY . .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Run the script
CMD ["python", "./wzxy.py"]
