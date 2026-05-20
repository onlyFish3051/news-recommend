from datetime import timezone

import datetime
from django.db import models


# Create your models here.


class News(models.Model):
    newsid = models.IntegerField(primary_key=True)
    newstitle = models.CharField(max_length=255)
    newscontent = models.TextField()
    newsdate = models.CharField(max_length=255)
    newsauthor = models.CharField(max_length=255)
    cid = models.IntegerField()
    newsimg = models.TextField()
    cname = models.CharField(max_length=255)
    seetimes = models.IntegerField(default=0)
    timeliness = models.IntegerField(default=100)
    likenumbers = models.IntegerField(default=0)
    commentnumbers = models.IntegerField(default=0)
    collectionnumbers = models.IntegerField(default=0)
    fire = models.FloatField(default=0)
    class_fire= models.FloatField(default=0)


class Like(models.Model):
    likeid = models.IntegerField(primary_key=True)
    news = models.ForeignKey(News, on_delete=models.CASCADE)
    uid = models.CharField(max_length=255)


class Newscomment(models.Model):
    commentid = models.IntegerField(primary_key=True)
    news = models.ForeignKey(News, on_delete=models.CASCADE)
    uid = models.CharField(max_length=255)
    comment = models.TextField()
    commenttime = models.DateTimeField(max_length=255, null=True)


class Newssee(models.Model):
    seeid = models.IntegerField(primary_key=True)
    news = models.ForeignKey(News, on_delete=models.CASCADE)
    uid = models.CharField(max_length=255)
    seetime = models.DateTimeField(max_length=255, null=True)


class User(models.Model):
    uid = models.CharField(primary_key=True, max_length=255)
    uname = models.CharField(max_length=255)
    passwd = models.CharField(max_length=255)
    email = models.CharField(max_length=255, null=True)
    phone = models.CharField(max_length=255, null=True)
    sex = models.CharField(max_length=30, null=True)
    img = models.TextField(null=True)
    word = models.TextField(null=True)
    usertype = models.IntegerField(default=2)
    province = models.CharField(max_length=255, null=True)
    birthdate = models.DateField(null=True)
    age = models.IntegerField(null=True)


class Collection(models.Model):
    collectionid = models.IntegerField(primary_key=True)
    news = models.ForeignKey(News, on_delete=models.CASCADE)
    uid = models.CharField(max_length=255)


class Newsrecommend(models.Model):
    id = models.IntegerField(primary_key=True)
    news = models.ForeignKey(News, on_delete=models.CASCADE)
    uid = models.CharField(max_length=255)
    cid = models.IntegerField()
    basefire = models.FloatField(default=0)
    addfire = models.FloatField(default=0)
    refire = models.FloatField(default=0)
    cos = models.FloatField(default=0)


class Newstype(models.Model):
    cid = models.IntegerField(primary_key=True)
    cname = models.CharField(max_length=255)
    typeimg = models.TextField(null=True)


class Img(models.Model):
    id = models.IntegerField(primary_key=True)
    imgurl = models.TextField(null=True)


class Userread(models.Model):
    id = models.IntegerField(primary_key=True)
    uid = models.CharField(max_length=255)
    readtime = models.IntegerField(default=0)
    readnumbers = models.IntegerField(default=0)
    datetime = models.DateTimeField()


class Userclouds(models.Model):
    id = models.IntegerField(primary_key=True)
    uid = models.CharField(max_length=255)
    cloudword = models.CharField(max_length=255)
    cloudtime = models.IntegerField(default=0, null=True)


class Uservisit(models.Model):
    id = models.IntegerField(primary_key=True)
    count = models.IntegerField(default=0)
    datetime = models.DateTimeField()


class Province(models.Model):
    id = models.IntegerField(primary_key=True)
    provincename = models.CharField(max_length=255, null=True)
