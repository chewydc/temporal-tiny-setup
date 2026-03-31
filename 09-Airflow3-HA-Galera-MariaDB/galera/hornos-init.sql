-- ============================================================================
-- GALERA CLUSTER - NODO HORNOS (Inicializador)
-- ============================================================================

-- Crear usuario de replicación Galera
CREATE USER IF NOT EXISTS 'galera_repl'@'%' IDENTIFIED BY 'galera_pass';
GRANT ALL PRIVILEGES ON *.* TO 'galera_repl'@'%' WITH GRANT OPTION;

-- Crear usuario para SST (State Snapshot Transfer)
CREATE USER IF NOT EXISTS 'sst_user'@'%' IDENTIFIED BY 'sst_pass';
GRANT RELOAD, LOCK TABLES, PROCESS, REPLICATION CLIENT ON *.* TO 'sst_user'@'%';

-- Configurar usuario de Airflow
GRANT ALL PRIVILEGES ON airflow.* TO 'airflow'@'%';

-- Configurar variables de Galera
SET GLOBAL wsrep_cluster_name = 'galera_cluster';
SET GLOBAL wsrep_node_name = 'hornos';

FLUSH PRIVILEGES;

-- Log de inicialización
SELECT 'GALERA HORNOS NODE INITIALIZED' as status;