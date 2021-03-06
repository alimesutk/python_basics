"""
Linux makinelerden hardware usage log bilgisini toplayıp database'de bir tabloya biriktiren ve farklı bir database tablosundaki alan ile de programı sonlandıran uygulama. :)
"""


""" Create Scripti
CREATE TABLE <schema_name>.LOG_MACHINE(
    CPU NUMBER,
    USED_MEMORY NUMBER,
    FREE_MEMORY NUMBER,
    PERCENT_MEMORY NUMBER,
    USED_DISK_M1 NUMBER,
    FREE_DISK_M1 NUMBER,
    PERCENT_DISK_M1 NUMBER,
    USED_DISK_M2 NUMBER,
    FREE_DISK_M2 NUMBER,
    PERCENT_DISK_M2 NUMBER,
    PERCENT_DISK_M_TOT NUMBER,
    CONTROL_DATE DATE
);

SELECT * FROM <schema_name>.LOG_MACHINE;
TRUNCATE TABLE <schema_name>.LOG_MACHINE;
"""

import paramiko
import cx_Oracle
import time
import pandas as pd

#1. makineye connection sağlanır
ssh_client = paramiko.SSHClient()
ssh_client.set_missing_host_key_policy (paramiko.AutoAddPolicy ())
ssh_client.connect(hostname=<hostname>, username=<username>, password=<password>)
ssh_client.invoke_shell()

#2. makineye connection sağlanır
ssh_client2 = paramiko.SSHClient()
ssh_client2.set_missing_host_key_policy (paramiko.AutoAddPolicy ())
ssh_client2.connect(hostname=<hostname>, username=<username>, password=<password>)
ssh_client2.invoke_shell()

#Insert işlemi yapılacak database'e connection sağlanır
con = cx_Oracle.connect('<username>/<password>@<hostname>:<port>/<sid>')
cur = con.cursor()
print(con.version)

#Programın sonlanması için kullanılacak sorgunun atılacağı database conection'ı sağlanır.
con2 = cx_Oracle.connect('<username>/<password>@<hostname>:<port>/<sid>')
print(con2.version)


while True:
    try:
        #----------------------------------------------LINUX MACHINE LOGS----------------------------------------------#

        print("-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-")

        #cpu bilgisini sar fonksiyonuyla dönen sonuçtan ayıklayıp alır.
        stdin, stdout, stderr = ssh_client.exec_command("sar -u 1 1 | awk 'NR==4 {print $3+$5}'") 
        cpu = ''.join(stdout.readlines())

        #memory bilgisini free -g fonksiyonuyla dönen sonuçtan ayıklayıp alır.
        stdin, stdout, stderr = ssh_client.exec_command("free -g | awk 'NR==2 {print $3}'") 
        used_memory = ''.join(stdout.readlines())
        stdin, stdout, stderr = ssh_client.exec_command("free -g | awk 'NR==2 {print $4}'")
        free_memory = ''.join(stdout.readlines())
        stdin, stdout, stderr = ssh_client.exec_command("free -g | awk 'NR==2 {print ($3)*100/($3+$4)}'")
        percent_memory = ''.join(stdout.readlines())

        #1. makineden df -BG fonksiyonu ile disk bilgisini alır.
        stdin, stdout, stderr = ssh_client.exec_command("df -BG | grep 'dpidata' | awk '{sum+=$2} END {print sum}'")
        used_disk_m1 = ''.join(stdout.readlines())
        stdin, stdout, stderr = ssh_client.exec_command("df -BG | grep 'dpidata' | awk '{sum+=$3} END {print sum}'")
        free_disk_m1 = ''.join(stdout.readlines())
        stdin, stdout, stderr = ssh_client.exec_command("df -BG | grep 'dpidata' | awk '{sum+=$4} END {print sum/2}'")
        percent_disk_m1 = ''.join(stdout.readlines())

        #2. makineden df -BG fonksiyonu ile disk bilgisini alır.
        stdin, stdout, stderr = ssh_client2.exec_command("df -BG | grep 'dpidata' | awk '{sum+=$2} END {print sum}'")
        used_disk_m2 = ''.join(stdout.readlines())
        stdin, stdout, stderr = ssh_client2.exec_command("df -BG | grep 'dpidata' | awk '{sum+=$3} END {print sum}'")
        free_disk_m2 = ''.join(stdout.readlines())
        stdin, stdout, stderr = ssh_client2.exec_command("df -BG | grep 'dpidata' | awk '{sum+=$4} END {print sum/2}'")
        percent_disk_m2 = ''.join(stdout.readlines())

        #2 makineden alınan bilgiler ile toplam yüzde kullanım bilgisi hesaplanır.
        percent_disk_m_tot = (float(percent_disk_m1)+float(percent_disk_m2))/2

        #Database'e göndermeden önce bu datalar formatlanır ve executemany içindeki insert ile append olarak tabloya yazılır.
        rows = [(float(cpu),float(used_memory),float(free_memory),float(percent_memory),int(used_disk_m1),float(free_disk_m1),
                 float(percent_disk_m1),float(used_disk_m2),float(free_disk_m2),float(percent_disk_m2),float(percent_disk_m_tot))]
        cur.executemany("insert into <schema_name>.LOG_MACHINE(CPU,USED_MEMORY,FREE_MEMORY,PERCENT_MEMORY,USED_DISK_M1,FREE_DISK_M1,PERCENT_DISK_M1,USED_DISK_M2,FREE_DISK_M2,PERCENT_DISK_M2,PERCENT_DISK_M_TOT,CONTROL_DATE) values (:1,:2,:3,:4,:5,:6,:7,:8,:9,:10,:11,SYSTIMESTAMP)", rows)
        con.commit()

        #log toplama için atılan sorguların sıklığını belirler
        time.sleep(60) 

    #control +c ile programı interrupt edip sonlandırır.
    except KeyboardInterrupt: 
        print("process interrupted")
        cur.close()
        con.close()
        exit()
        raise
    
    #Database üzerinde log toplama sürecini tamamlaması için başka bir tablodan ver kontrolü sağlanır.
    plan_end_flag_query = "SELECT STATUS FROM <schema_name>.PLAN_TABLE WHERE PLAN = 'DAILY' AND JOB LIKE '%DAY_END%' AND TRUNC(END_DATE) = TRUNC(SYSDATE)" 
    plan_end_flag_df = pd.read_sql(plan_end_flag_query, con=con2)
    plan_end_flag = plan_end_flag_df.iloc[0,0]
    if (plan_end_flag == 'COMPLETED'):
        break

cur.close()
con.close()
exit()

