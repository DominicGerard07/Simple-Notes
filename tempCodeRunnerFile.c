#include <stdio.h>
#include <stdlib.h>

#define MAX 50

typedef struct {
    int id, bt, pr, rem, ct, wt, tat;
} Job;

void copyJobs(Job dst[], Job src[], int n) {
    for (int i=0;i<n;i++) dst[i]=src[i];
}

void printResult(Job a[], int n, const char *name) {
    double sw=0, st=0;
    printf("\n%s\n", name);
    printf("Job\tBT\tPR\tCT\tWT\tTAT\n");
    for(int i=0;i<n;i++){
        a[i].tat=a[i].ct;
        a[i].wt=a[i].tat-a[i].bt;
        sw+=a[i].wt; st+=a[i].tat;
        printf("J%d\t%d\t%d\t%d\t%d\t%d\n",
               a[i].id,a[i].bt,a[i].pr,a[i].ct,a[i].wt,a[i].tat);
    }
    printf("Average WT  : %.2f\n", sw/n);
    printf("Average TAT : %.2f\n", st/n);
}

void fcfs(Job a[], int n) {
    int time=0;
    printf("\nGantt: ");
    for(int i=0;i<n;i++){
        printf("J%d ",a[i].id);
        time+=a[i].bt;
        a[i].ct=time;
    }
    printf("\n");
    printResult(a,n,"FCFS Scheduling");
}

void sjf(Job a[], int n) {
    int time=0;
    for(int i=0;i<n-1;i++)
        for(int j=i+1;j<n;j++)
            if(a[j].bt<a[i].bt){ Job t=a[i]; a[i]=a[j]; a[j]=t; }
    printf("\nGantt: ");
    for(int i=0;i<n;i++){
        printf("J%d ",a[i].id);
        time+=a[i].bt;
        a[i].ct=time;
    }
    printf("\n");
    printResult(a,n,"SJF Scheduling");
}

void priority(Job a[], int n) {
    int time=0;
    for(int i=0;i<n-1;i++)
        for(int j=i+1;j<n;j++)
            if(a[j].pr<a[i].pr){ Job t=a[i]; a[i]=a[j]; a[j]=t; }
    printf("\nGantt: ");
    for(int i=0;i<n;i++){
        printf("J%d ",a[i].id);
        time+=a[i].bt;
        a[i].ct=time;
    }
    printf("\n");
    printResult(a,n,"Priority Scheduling");
}

void roundRobin(Job a[], int n, int q) {
    int time=0, done=0, front=0, rear=0, qx[MAX*MAX];
    for(int i=0;i<n;i++){ a[i].rem=a[i].bt; qx[rear++]=i; }
    printf("\nGantt: ");
    while(done<n){
        int k=qx[front++];
        if(a[k].rem>q){
            printf("J%d ",a[k].id);
            time+=q; a[k].rem-=q; qx[rear++]=k;
        } else {
            printf("J%d ",a[k].id);
            time+=a[k].rem; a[k].rem=0; a[k].ct=time; done++;
        }
    }
    printf("\n");
    printResult(a,n,"Round Robin Scheduling");
}

int main(void){
    Job base[MAX], a[MAX];
    int n, choice, q;
    printf("JOB SCHEDULING SYSTEM\n");
    printf("Enter number of jobs: ");
    scanf("%d",&n);
    for(int i=0;i<n;i++){
        base[i].id=i+1;
        printf("Enter burst time and priority for J%d: ",i+1);
        scanf("%d%d",&base[i].bt,&base[i].pr);
    }
    do{
        printf("\n1.FCFS  2.SJF  3.Priority  4.Round Robin  5.Exit\n");
        printf("Enter choice: ");
        scanf("%d",&choice);
        copyJobs(a,base,n);
        switch(choice){
            case 1: fcfs(a,n); break;
            case 2: sjf(a,n); break;
            case 3: priority(a,n); break;
            case 4:
                printf("Enter time quantum: ");
                scanf("%d",&q);
                roundRobin(a,n,q); break;
            case 5: printf("Program ended.\n"); break;
            default: printf("Invalid choice.\n");
        }
    }while(choice!=5);
    return 0;
}
