-- Primary MariaDB initialization
-- Creates replication user, MaxScale monitor user, and Airflow database

CREATE DATABASE IF NOT EXISTS airflow;

-- Replication user (used by replica to connect to primary)
CREATE USER IF NOT EXISTS 'repl_user'@'%' IDENTIFIED BY 'repl_pass';
GRANT REPLICATION SLAVE ON *.* TO 'repl_user'@'%';

-- MaxScale monitor user (used by MaxScale to check server health and execute failover)
CREATE USER IF NOT EXISTS 'maxscale_monitor'@'%' IDENTIFIED BY 'maxscale_monitor_pass';
GRANT REPLICATION CLIENT, REPLICATION SLAVE, SUPER, RELOAD, PROCESS, SHOW DATABASES, EVENT, READ_ONLY ADMIN ON *.* TO 'maxscale_monitor'@'%';

-- MaxScale routing user (used by MaxScale to route queries)
CREATE USER IF NOT EXISTS 'maxscale_router'@'%' IDENTIFIED BY 'maxscale_router_pass';
GRANT SELECT ON mysql.user TO 'maxscale_router'@'%';
GRANT SELECT ON mysql.db TO 'maxscale_router'@'%';
GRANT SELECT ON mysql.tables_priv TO 'maxscale_router'@'%';
GRANT SELECT ON mysql.columns_priv TO 'maxscale_router'@'%';
GRANT SELECT ON mysql.proxies_priv TO 'maxscale_router'@'%';
GRANT SELECT ON mysql.roles_mapping TO 'maxscale_router'@'%';
GRANT SHOW DATABASES ON *.* TO 'maxscale_router'@'%';

-- Airflow user (used by Airflow through MaxScale)
CREATE USER IF NOT EXISTS 'airflow'@'%' IDENTIFIED BY 'airflow_pass';
GRANT ALL PRIVILEGES ON airflow.* TO 'airflow'@'%';

FLUSH PRIVILEGES;
