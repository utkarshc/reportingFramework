import boto3
import datetime
import matplotlib.pyplot as plt
import argparse
import sys
import ses_utils2 as SES

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
    totalOk = 0.0;
    totalFail = 0.0;
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
        totalFail += errCount;
        totalOk += okCount;

    if(totalOk == 0.0) :
        avg = 0.0;
    else  :
        avg = totalOk / (totalOk + totalFail)
    return {"x" : xes, "y" : yes, "avg" : avg};

def getCommandLineArgs() :
    parser = argparse.ArgumentParser();
    parser.add_argument("--caller", help="The engine for which you want to generate logs. Default : game_engine", default="game_engine", choices=["game_engine","content_engine"]);
    parser.add_argument("--days", help="last n days for which we want the graphs. Default : 1", default=1, type=int, choices=[1,2,3,4,5,6,7]);
    parser.add_argument("--env", help="environment variable that is given on cloudwatch", required=True);
    parser.add_argument("--add_to_s3", help="do you want to upload the graphs to s3", dest='addS3', action='store_true');
    parser.set_defaults(addS3=False)
    parser.add_argument("--send_mail", help="do you want to send the mail", dest='sendMail', action='store_true');
    parser.set_defaults(sendMail=False)
    parser.add_argument("--mailid", help="email id where to send");
    args = parser.parse_args();
    if args.sendMail and args.mailid == None:
        parser.print_help();
        sys.exit();
    return args;

def getFileNameToSave(caller, datetime) :
    return caller + str(datetime) + ".png"

if __name__ == "__main__":
    args = getCommandLineArgs();
    DAYS_REPORT = args.days;
    DIM_ENV_VALUE = args.env;
    caller = args.caller
    cwModel = CwModel("infra_metric", caller);
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
        plt.plot(successPercentageStats["x"],successPercentageStats["y"], label=(callee + " (avg success " + str(successPercentageStats["avg"]) + ")"));
        axes = plt.gca();
        axes.set_ylim([-0.1,1.1]);
    plt.legend();
    filename = getFileNameToSave(caller, datetime.datetime.now())
    plt.savefig(filename);
    ses = SES.SESClient();
    ses.send_email("utkarsh.c@mindtickle.com", ["utkarsh.c@mindtickle.com","arpit.goyal@mindtickle.com","sumit.jha@mindtickle.com"], "the subject", "", [filename]);
    # plt.show();

    # print(str(metrics));
    # sys.exit();
