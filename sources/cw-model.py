import boto3
import datetime
import numpy
import matplotlib.pyplot as plt

DIM_ENV_NAME="environment";
DIM_ENV_VALUE="infra.mindtickle.com";
SUM_STATS = "Sum";
METRIC_NAME="application-health";
DIM_CALLER="caller";
DIM_CALLEE="callee";
DIM_STATUS_CODE="statusCode";
DAYS_REPORT=1;
OK_STATUS='200';
CL_ERR_STATUS='400';
SV_ERR_STATUS='500';

class CwModel :
    def __init__(self, namespace, caller):
        self.namespace = namespace;
        self.caller = caller;
        self.cloudwatch = boto3.client('cloudwatch')

    def getMetrics(self):
        return self.cloudwatch.list_metrics(
            Namespace=self.namespace,
            MetricName=METRIC_NAME,
            Dimensions=[
                {
                    'Name': DIM_CALLER,
                    'Value': self.caller
                },
                {
                    'Name': DIM_ENV_NAME,
                    'Value': DIM_ENV_VALUE
                }
            ]
        );

    def getDataForMetrics(self, metrics, endTime, period):
        startTime = endTime - datetime.timedelta(days=DAYS_REPORT);
        dataMap = {};
        for metric in metrics:
            statistics = self.cloudwatch.get_metric_statistics(
                Namespace=self.namespace,
                MetricName=METRIC_NAME,
                Dimensions=metric["Dimensions"],
                StartTime=startTime,
                EndTime=endTime,
                Period=period,
                Statistics=[
                    SUM_STATS,
                ]
            );
            if(statistics and statistics.has_key("Datapoints")) :
                dataMap[getDimensionValue(DIM_STATUS_CODE, metric["Dimensions"])] = statistics["Datapoints"];
        # print(str(dataMap));
        return dataMap;

def getDimensionValue(dimName, dimensions) :
    for dim in dimensions:
        if(dim['Name'] == dimName):
            return dim['Value'];

def getUniqueCallees(metrics) :
    uniqueCallees = [];
    for i in metrics:
        dims = i["Dimensions"];
        for j in dims:
            if(j['Name'] == DIM_CALLEE):
                callee = j['Value']
                if(callee not in uniqueCallees) :
                    uniqueCallees.append(callee);
    return uniqueCallees;

def getCalleeWiseSegregateMetrics(metrics) :
    calleeWiseSegregate = {};
    for i in metrics:
        dims = i["Dimensions"];
        for j in dims:
            if(j['Name'] == DIM_CALLEE):
                callee = j['Value']
                if(not calleeWiseSegregate.has_key(callee)) :
                    calleeWiseSegregate[callee] = [];
                calleeWiseSegregate[callee].append(i);
                break;
    return calleeWiseSegregate;

def getTime(datapoint) :
    return datapoint["Timestamp"]

def sortByTimeDatapoints(datapoints) :
    return sorted(datapoints, key=getTime);

def generateSuccessPercentageStats(okStatusStats, clErrStatusStats, svErrStatusStats) :
    xes = [];
    yes = [];
    allStats = [];
    for stat in okStatusStats:
        stat['status'] = OK_STATUS;
        allStats.append(stat);
    for stat in clErrStatusStats:
        stat['status'] = CL_ERR_STATUS;
        allStats.append(stat);
    for stat in svErrStatusStats:
        stat['status'] = SV_ERR_STATUS;
        allStats.append(stat);

    allStats = sortByTimeDatapoints(allStats);

    idx = -1;
    while idx+1 < len(allStats) :
        idx += 1;
        currTime = allStats[idx]["Timestamp"];
        allCurrStats = [allStats[idx]];
        while True :
            if idx+1 < len(allStats) and currTime == allStats[idx+1]["Timestamp"]:
                idx += 1;
                allCurrStats.append(allStats[idx]);
            else :
                break;
        okCount = 0.0;
        errCount = 0.0;
        for stat in allCurrStats :
            if stat['status'] == OK_STATUS:
                okCount += stat[SUM_STATS];
            else :
                errCount += stat[SUM_STATS];

        xes.append(currTime);
        if(okCount == 0.0) :
            yes.append(0.0);
        else :
            yes.append(okCount / (okCount + errCount));
    return {"x" : xes, "y" : yes};


if __name__ == "__main__":
    cwModel = CwModel("infra_metric", "game_engine");
    metrics = cwModel.getMetrics();
    calleeWiseSegregatedMetrics = getCalleeWiseSegregateMetrics(metrics['Metrics']);
    for callee in calleeWiseSegregatedMetrics :
        allCalleeMetrics = calleeWiseSegregatedMetrics[callee];
        statusWiseStats = cwModel.getDataForMetrics(allCalleeMetrics, datetime.datetime.now(), 120);

        # if no data points found for this callee, we'll skip this callee's stats
        if not statusWiseStats:
            continue;

        # for statusCode in statusWiseStats :
        #     sortByTimeDatapoints(statusWiseStats[statusCode]);
        #
        if statusWiseStats.has_key(OK_STATUS) :
            okStatusStats = statusWiseStats[OK_STATUS];
        else :
            okStatusStats = [];
        if statusWiseStats.has_key(CL_ERR_STATUS) :
            clErrStatusStats = statusWiseStats[CL_ERR_STATUS];
        else :
            clErrStatusStats = [];
        if statusWiseStats.has_key(SV_ERR_STATUS) :
            svErrStatusStats = statusWiseStats[SV_ERR_STATUS];
        else :
            svErrStatusStats = [];

        successPercentageStats = generateSuccessPercentageStats(okStatusStats, clErrStatusStats, svErrStatusStats);
        plt.plot(successPercentageStats["x"],successPercentageStats["y"], label=callee);
        axes = plt.gca();
        axes.set_ylim([-0.1,1.1]);
    plt.legend();
    plt.savefig('plot.png');
    # plt.show();

    print(str(metrics));
