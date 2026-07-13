---
document_type: prd
title: "{{ title }}"
author: "{{ author }}"
date: "{{ date }}"
status: "{{ status | default('draft') }}"
---
# {{ title }}

## 1. Introduction
{{ introduction }}

## 2. Objectives
{{ objectives }}

## 3. Scope
{{ scope }}

## 4. Requirements
{{ requirements }}

## 5. User Stories
{{ user_stories }}

## 6. Success Metrics
{{ success_metrics }}
