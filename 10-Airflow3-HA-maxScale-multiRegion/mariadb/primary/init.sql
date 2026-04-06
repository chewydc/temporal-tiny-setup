-- ============================================================================
-- MARIADB PRIMARY - HORNOS
-- ============================================================================
-- Configuración basada en caso 08 que funciona
-- ============================================================================

CREATE DATABASE IF NOT EXISTS airflow;

-- Usuario de replicación (usado por replicas)
CREATE USER IF NOT EXISTS 'repl_user'@'%' IDENTIFIED BY 'repl_pass';
GRANT REPLICATION SLAVE ON *.* TO 'repl_user'@'%';

-- Usuario MaxScale monitor (IGUAL A PRODUCCIÓN)
CREATE USER IF NOT EXISTS 'monitor'@'%' IDENTIFIED BY 'monitor_pass';
GRANT REPLICA MONITOR ON *.* TO 'monitor'@'%';
GRANT REPLICATION CLIENT, REPLICATION SLAVE, SUPER, RELOAD, PROCESS, SHOW DATABASES, EVENT ON *.* TO 'monitor'@'%';
GRANT SELECT ON mysql.* TO 'monitor'@'%';
GRANT EXECUTE ON mysql.* TO 'monitor'@'%';

-- Usuario MaxScale router (IGUAL A PRODUCCIÓN)
CREATE USER IF NOT EXISTS 'maxscaleuser'@'%' IDENTIFIED BY 'router_pass';
GRANT SELECT ON mysql.user TO 'maxscaleuser'@'%';
GRANT SELECT ON mysql.db TO 'maxscaleuser'@'%';
GRANT SELECT ON mysql.tables_priv TO 'maxscaleuser'@'%';
GRANT SELECT ON mysql.columns_priv TO 'maxscaleuser'@'%';
GRANT SELECT ON mysql.proxies_priv TO 'maxscaleuser'@'%';
GRANT SELECT ON mysql.roles_mapping TO 'maxscaleuser'@'%';
GRANT SHOW DATABASES ON *.* TO 'maxscaleuser'@'%';
GRANT EXECUTE ON mysql.* TO 'maxscaleuser'@'%';

-- Usuario Airflow (usado por Airflow a través de MaxScale)
CREATE USER IF NOT EXISTS 'airflow'@'%' IDENTIFIED BY 'airflow_pass';
GRANT ALL PRIVILEGES ON airflow.* TO 'airflow'@'%';

FLUSH PRIVILEGES;

-- Log de inicialización
SELECT 'PRIMARY HORNOS INITIALIZED' as status;
