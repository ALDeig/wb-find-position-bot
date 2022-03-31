create table users(
    user_id varchar(50) primary key
);

create table subscribe(
    subscribe_id varchar(50) primary key,
    scu integer,
    query_text TEXT,
    user_id varchar(50),
    page integer,
    position integer
);

create table query(
    query_id varchar(40) primary key,
    scu varchar(30),
    query_text text,
    page integer,
    position integer,
    created_at text
);

create table messages(
    name varchar(50) primary key,
    message text
);
