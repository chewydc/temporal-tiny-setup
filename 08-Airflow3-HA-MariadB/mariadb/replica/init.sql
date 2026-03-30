-- Replica MariaDB initialization
-- Connects to primary and starts replication

CHANGE MASTER TO
    MASTER_HOST='mariadb-primary',
    MASTER_PORT=3306,
    MASTER_USER='repl_user',
    MASTER_PASSWORD='repl_pass',
    MASTER_CONNECT_RETRY=10,
    MASTER_USE_GTID=slave_pos;

START SLAVE;
