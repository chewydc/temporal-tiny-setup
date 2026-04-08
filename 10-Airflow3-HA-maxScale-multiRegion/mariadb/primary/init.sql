-- ============================================================================
-- MARIADB PRIMARY - HORNOS (VERSIÓN CORREGIDA Y SEGURA)
-- ============================================================================

CREATE DATABASE IF NOT EXISTS airflow;

-- Replication user (used by replica to connect to primary)
CREATE USER IF NOT EXISTS 'repl_user'@'%' IDENTIFIED BY 'repl_pass';
GRANT REPLICATION SLAVE ON *.* TO 'repl_user'@'%';

-- MaxScale monitor user (used by MaxScale to check server health and execute failover)
CREATE USER IF NOT EXISTS 'monitor'@'%' IDENTIFIED BY 'monitor_pass';
GRANT REPLICA MONITOR ON *.* TO 'monitor'@'%';
GRANT REPLICATION CLIENT, REPLICATION SLAVE, SUPER, RELOAD, PROCESS, SHOW DATABASES, EVENT, READ_ONLY ADMIN ON *.* TO 'monitor'@'%';
GRANT SELECT ON mysql.* TO 'monitor'@'%';
GRANT EXECUTE ON mysql.* TO 'monitor'@'%';

-- MaxScale routing user (used by MaxScale to route queries)
CREATE USER IF NOT EXISTS 'maxscaleuser'@'%' IDENTIFIED BY 'router_pass';
GRANT SELECT ON mysql.user TO 'maxscaleuser'@'%';
GRANT SELECT ON mysql.db TO 'maxscaleuser'@'%';
GRANT SELECT ON mysql.tables_priv TO 'maxscaleuser'@'%';
GRANT SELECT ON mysql.columns_priv TO 'maxscaleuser'@'%';
GRANT SELECT ON mysql.proxies_priv TO 'maxscaleuser'@'%';
GRANT SELECT ON mysql.roles_mapping TO 'maxscaleuser'@'%';
GRANT SHOW DATABASES ON *.* TO 'maxscaleuser'@'%';
GRANT EXECUTE ON mysql.* TO 'maxscaleuser'@'%';

-- Airflow user (used by Airflow through MaxScale)
CREATE USER IF NOT EXISTS 'airflow'@'%' IDENTIFIED BY 'airflow_pass';
GRANT ALL PRIVILEGES ON airflow.* TO 'airflow'@'%';

FLUSH PRIVILEGES;
