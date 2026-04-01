-- ============================================================================
-- MARIADB PRIMARY - HORNOS
-- ============================================================================
-- Configuración basada en caso 08 que funciona
-- ============================================================================

CREATE DATABASE IF NOT EXISTS airflow;

-- Usuario de replicación (usado por replicas)
CREATE USER IF NOT EXISTS 'repl_user'@'%' IDENTIFIED BY 'repl_pass';
GRANT REPLICATION SLAVE ON *.* TO 'repl_user'@'%';

-- Usuario MaxScale monitor (usado por MaxScale para monitoreo y failover)
CREATE USER IF NOT EXISTS 'maxscale_monitor'@'%' IDENTIFIED BY 'monitor_pass';
GRANT REPLICATION CLIENT, REPLICATION SLAVE, SUPER, RELOAD, PROCESS, SHOW DATABASES, EVENT ON *.* TO 'maxscale_monitor'@'%';
GRANT SELECT ON mysql.* TO 'maxscale_monitor'@'%';

-- Usuario MaxScale router (usado por MaxScale para routing de queries)
CREATE USER IF NOT EXISTS 'maxscale_router'@'%' IDENTIFIED BY 'router_pass';
GRANT SELECT ON mysql.user TO 'maxscale_router'@'%';
GRANT SELECT ON mysql.db TO 'maxscale_router'@'%';
GRANT SELECT ON mysql.tables_priv TO 'maxscale_router'@'%';
GRANT SELECT ON mysql.columns_priv TO 'maxscale_router'@'%';
GRANT SELECT ON mysql.proxies_priv TO 'maxscale_router'@'%';
GRANT SELECT ON mysql.roles_mapping TO 'maxscale_router'@'%';
GRANT SHOW DATABASES ON *.* TO 'maxscale_router'@'%';

-- Usuario Airflow (usado por Airflow a través de MaxScale)
CREATE USER IF NOT EXISTS 'airflow'@'%' IDENTIFIED BY 'airflow_pass';
GRANT ALL PRIVILEGES ON airflow.* TO 'airflow'@'%';

FLUSH PRIVILEGES;

-- Log de inicialización
SELECT 'PRIMARY HORNOS INITIALIZED' as status;
