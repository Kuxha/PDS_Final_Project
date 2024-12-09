-- Drop the existing database and recreate it
DROP DATABASE IF EXISTS WelcomeHome;
CREATE DATABASE WelcomeHome;
USE WelcomeHome;

-- Add new columns for features
-- Note: Ensure this is after tables are created if modifying existing schema
-- ALTER TABLE Item ADD isAvailable BOOLEAN DEFAULT TRUE; -- Removed as handled in creation
-- ALTER TABLE Ordered ADD notes VARCHAR(255); -- Removed as handled in creation

-- Drop all tables in reverse order of dependency to avoid foreign key issues
DROP TABLE IF EXISTS Delivered;
DROP TABLE IF EXISTS ItemIn;
DROP TABLE IF EXISTS Ordered;
DROP TABLE IF EXISTS Piece;
DROP TABLE IF EXISTS Location;
DROP TABLE IF EXISTS Act;
DROP TABLE IF EXISTS Role;
DROP TABLE IF EXISTS DonatedBy;
DROP TABLE IF EXISTS PersonPhone;
DROP TABLE IF EXISTS Person;
DROP TABLE IF EXISTS Item;
DROP TABLE IF EXISTS Category;

-- Create Category table
CREATE TABLE Category (
    mainCategory VARCHAR(50) NOT NULL,
    subCategory VARCHAR(50) NOT NULL,
    catNotes TEXT,
    PRIMARY KEY (mainCategory, subCategory)
);

select * from Ordered;
DESCRIBE Ordered;
SELECT * FROM ItemIn;

select * from Person;
select * from Piece;
select * from Item;
DESCRIBE Piece;

select * from Person;
-- Create Item table
CREATE TABLE Item (
    ItemID INT NOT NULL AUTO_INCREMENT,
    iDescription TEXT,
    photo VARCHAR(20),
    color VARCHAR(20),
    isNew BOOLEAN DEFAULT TRUE,
    hasPieces BOOLEAN,
    material VARCHAR(50),
    mainCategory VARCHAR(50) NOT NULL,
    subCategory VARCHAR(50) NOT NULL,
    PRIMARY KEY (ItemID),
    FOREIGN KEY (mainCategory, subCategory) REFERENCES Category(mainCategory, subCategory)
);

-- Create Person table
CREATE TABLE Person (
    userName VARCHAR(50) NOT NULL,
    password VARCHAR(255) NOT NULL,
    fname VARCHAR(50) NOT NULL,
    lname VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL,
    PRIMARY KEY (userName)
);

-- Create PersonPhone table
CREATE TABLE PersonPhone (
    userName VARCHAR(50) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    PRIMARY KEY (userName, phone),
    FOREIGN KEY (userName) REFERENCES Person(userName)
);

-- Create DonatedBy table
CREATE TABLE DonatedBy (
    ItemID INT NOT NULL,
    userName VARCHAR(50) NOT NULL,
    donateDate DATE NOT NULL,
    PRIMARY KEY (ItemID, userName),
    FOREIGN KEY (ItemID) REFERENCES Item(ItemID),
    FOREIGN KEY (userName) REFERENCES Person(userName)
);

-- Create Role table
CREATE TABLE Role (
    roleID VARCHAR(20) NOT NULL,
    rDescription VARCHAR(100),
    PRIMARY KEY (roleID)
);

-- Create Act table
CREATE TABLE Act (
    userName VARCHAR(50) NOT NULL,
    roleID VARCHAR(20) NOT NULL,
    PRIMARY KEY (userName, roleID),
    FOREIGN KEY (userName) REFERENCES Person(userName),
    FOREIGN KEY (roleID) REFERENCES Role(roleID)
);

-- Create Location table
CREATE TABLE Location (
    roomNum INT NOT NULL,
    shelfNum INT NOT NULL,
    shelf VARCHAR(20),
    shelfDescription VARCHAR(200),
    PRIMARY KEY (roomNum, shelfNum)
);

-- Create Piece table
-- Removed copyID and reverted to pieceNum
CREATE TABLE Piece (
    ItemID INT NOT NULL,
    pieceNum INT NOT NULL,
    pDescription VARCHAR(200),
    length INT NOT NULL,
    width INT NOT NULL,
    height INT NOT NULL,
    roomNum INT NOT NULL,
    shelfNum INT NOT NULL, 
    pNotes TEXT,
    PRIMARY KEY (ItemID, pieceNum),
    FOREIGN KEY (ItemID) REFERENCES Item(ItemID),
    FOREIGN KEY (roomNum, shelfNum) REFERENCES Location(roomNum, shelfNum)
);

-- Create Ordered table
CREATE TABLE Ordered (
    orderID INT NOT NULL AUTO_INCREMENT,
    orderDate DATE NOT NULL,
    orderNotes VARCHAR(200),
    supervisor VARCHAR(50) NOT NULL,
    client VARCHAR(50) NOT NULL,
    PRIMARY KEY (orderID),
    FOREIGN KEY (supervisor) REFERENCES Person(userName),
    FOREIGN KEY (client) REFERENCES Person(userName)
);

-- Create ItemIn table
CREATE TABLE ItemIn (
    ItemID INT NOT NULL,
    pieceNum INT NOT NULL,
    orderID INT NOT NULL,
    found BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (ItemID, pieceNum, orderID),
    FOREIGN KEY (ItemID, pieceNum) REFERENCES Piece(ItemID, pieceNum),
    FOREIGN KEY (orderID) REFERENCES Ordered(orderID)
);

-- Create Delivered table
CREATE TABLE Delivered (
    userName VARCHAR(50) NOT NULL,
    orderID INT NOT NULL,
    status VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    PRIMARY KEY (userName, orderID),
    FOREIGN KEY (userName) REFERENCES Person(userName),
    FOREIGN KEY (orderID) REFERENCES Ordered(orderID)
);

-- Insert Roles
INSERT INTO Role (roleID, rDescription) VALUES ('staff', 'Staff Member');
INSERT INTO Role (roleID, rDescription) VALUES ('volunteer', 'Volunteer Member');

-- Insert Locations
INSERT INTO Location (roomNum, shelfNum, shelf, shelfDescription)
VALUES (100, 1, 'A1', 'Front room shelf'),
       (200, 2, 'B2', 'Back room upper shelf'),
       (300, 1, 'C1', 'Storage closet shelf');

-- Insert Categories
INSERT INTO Category (mainCategory, subCategory, catNotes)
VALUES ('Furniture', 'Chair', 'Chairs of various types'),
       ('Furniture', 'Table', 'Different styles of tables'),
       ('Electronics', 'TV', 'Television sets'),
       ('Clothing', 'Shirt', 'All kinds of shirts');

-- Insert Persons
INSERT INTO Person (userName, password, fname, lname, email)
VALUES ('staffUser', 'staffpass', 'Staff', 'Member', 'staff@example.com'),
       ('volUser', 'volpass', 'Vol', 'User', 'volunteer@example.com'),
       ('donorUser', 'donorpass', 'Donor', 'User', 'donor@example.com'),
       ('clientUser', 'clientpass', 'Client', 'User', 'client@example.com');

-- Assign Roles
INSERT INTO Act (userName, roleID) VALUES ('staffUser', 'staff'), ('volUser', 'volunteer');
-- Insert roles into the Act table

select * from Act;
SELECT * FROM Person WHERE userName = 'clientUser';
SELECT * FROM Act WHERE userName = 'clientUser' AND roleID = 'client';

INSERT INTO Role (roleID, rDescription) VALUES ('client', 'Client User');

-- Insert Items
INSERT INTO Item (iDescription, mainCategory, subCategory, isNew, material, color)
VALUES ('Wooden dining chair', 'Furniture', 'Chair', TRUE, 'Wood', 'Brown'),
       ('Office swivel chair', 'Furniture', 'Chair', FALSE, 'Metal/Cloth', 'Black'),
       ('Coffee table', 'Furniture', 'Table', TRUE, 'Wood', 'Brown'),
       ('T-Shirt', 'Clothing', 'Shirt', TRUE, 'Cotton', 'White');

-- Insert Pieces
INSERT INTO Piece (ItemID, pieceNum, pDescription, length, width, height, roomNum, shelfNum)
VALUES (1, 1, 'Dining chair piece', 40, 40, 90, 100, 1),
       (2, 1, 'Office chair piece', 45, 45, 100, 200, 2),
       (3, 1, 'Coffee table piece', 60, 60, 45, 300, 1);

-- Insert Orders
INSERT INTO Ordered (orderDate, orderNotes, supervisor, client)
VALUES ('2024-02-01', 'Client needs a chair', 'staffUser', 'clientUser');

-- Insert ItemIn
INSERT INTO ItemIn (ItemID, pieceNum, orderID, found) VALUES (1, 1, 1, FALSE);

-- Insert Delivered
INSERT INTO Delivered (userName, orderID, status, date) VALUES ('volUser', 1, 'Delivered', '2024-02-05');


SELECT * FROM Act WHERE userName = 'clientUser';

