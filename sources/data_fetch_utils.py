import boto3
import datetime

import numpy
import matplotlib.pyplot as plt

import random

# Create CloudWatch client
cloudwatch = boto3.client('cloudwatch')

# List metrics through the pagination interface
metric = cloudwatch.get_metric_statistics(
    Namespace='AWS/EC2',
    MetricName='CPUUtilization',
    Dimensions=[
        {
            "Value": "allaboardASG",
            "Name": "AutoScalingGroupName"
        }],
    StartTime=datetime.datetime(2018, 3, 7),
    EndTime=datetime.datetime(2018, 3, 9),
    Period=3600,
    Statistics=[
        'Average',
    ]);

# # List metrics through the pagination interface
# metric = cloudwatch.get_metric_statistics(
#     Namespace='infra-metric',
#     MetricName='infra-content-engine',
#     # MetricName='application-health',
#     Dimensions=[
#         {
#             "Name": "method",
#             "Value": "getCompanySettings"
#         }],
#     StartTime=datetime.datetime(2018, 3, 9),
#     EndTime=datetime.datetime(2018, 3, 10),
#     Period=3600,
#     Statistics=[
#         'Average',
#     ]);

datapoints = metric['Datapoints'];
# print(str(datapoints))

def getTime(datapoint) :
    return datapoint["Timestamp"]

def sortByTimeDatapoints(datapoints) :
    return sorted(datapoints, key=getTime);

datapoints = sortByTimeDatapoints(datapoints);

def getAllCounts(datapoints) :
    ret = [];
    for i in datapoints:
        ret.append([i["Average"]]);
    return ret;

def getAllTimeStamps(datapoints) :
    ret = [];
    for i in datapoints:
        ret.append([i["Timestamp"]]);
    return ret;

def getAllTimeStamps2(datapoints) :
    ret = [];
    for i in datapoints:
        i["Timestamp"] += datetime.timedelta(hours=2);
        ret.append([i["Timestamp"]]);
    return ret;

y = getAllCounts(datapoints);
x = getAllTimeStamps(datapoints);
x1 = getAllTimeStamps2(datapoints);

plt.plot(x,y);
plt.plot(x1,y);
plt.show();

# data = [go.Scatter(x=x, y=y)];
#
# py.iplot(data)

# print(str(datapoints))