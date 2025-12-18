# **Database Schema Design**

## Overview
This schema is designed to store and analyze Google Play reviews for the ChatGPT application.
The goal is to support exploratory data analysis (EDA), temporal trend analysis, and future extensions.
The schema separates application metadata from user reviews, following a simple relational design that supports efficient querying over time.

## Tables
1. apps
This table stores metadata about the application being analyzed.
There are three columns in this table, which are app_id, app_name,and platform.
· app_id : INTEGER ; Unique identifier for the application.
· app_name : TEXT ; Name of the application.
· platform : TEXT ; Platform where reviews are collected.
2. reviews
This table stores individual user reviews and associated metadata.
There are nine columns in this table, which are review_id, app_id, user_name, rating, review_text, review_date, year_month, app_version, text_length.
· review_id : INTEGER ; Unique identifier for each review.
· app_id : INTEGER ; References apps.app_id.
· user_name : TEXT ; Reviews author name.
· rating : INTEGER ; Review rating.
· review_text : TEXT ; Full textual content of the review.
· review_date : DATE ; Timestamp when the review was posted.
· year_month : TEXT ; Year-month bucket derived from review_date.
· app_version : TEXT ; App version associated with the review.
· text_length : INTEGER ; Number of words in the review text.

## Relationship
reviews.app_id → apps.app_id