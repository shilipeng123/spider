# -*- coding: utf-8 -*-
import scrapy
import re
import json
from scrapy import Request
from xpc.items import PostItem,CommentItem,ComposerItem,CopyrightItem


strip = lambda x: x.strip() if x else ''

def convert_int(s):
    if s:
        return int(s.replace(',',''))
    return 0

ci = convert_int


class DiscoverySpider(scrapy.Spider):
    name = 'discovery'
    allowed_domains = ['xinpianchang.com','openapi-vtom.vmovier.com']
    start_urls = ['http://www.xinpianchang.com/channel/index/sort-like?from=tabArticle']

    def parse(self, response):
        url = 'http://www.xinpianchang.com/a%s?from=ArticleList'
        post_list = response.xpath("//ul[@class='video-list']/li")
        for post in post_list:
            pid = post.xpath('./@data-articleid').extract_first()
            request = Request(url % pid,callback=self.parse_post)
            request.meta['pid'] = pid
            request.meta['thumbnail'] = post.xpath('./a/img/@_src').get()
            yield request

    def parse_post(self, response):
        pid = response.meta['pid']
        post = PostItem()
        post['pid'] =  pid
        post['thumbnail'] = response.meta['thumbnail']
        # post["video"] = response.xpath("//video[@id='xpc_video']/@src").extract_first()
        post['title'] = response.xpath(
            '//div[@class="title-wrap"]/h3/text()').extract_first()
        cates = response.xpath(
            '//span[contains(@class, "cate")]/a/text()').extract()
        post['category'] = '-'.join([cate.strip() for cate in cates])
        post['created_at'] = response.xpath(
            '//span[contains(@class, "update-time")]/i/text()').get()
        post['play_counts'] = response.xpath(
            '//i[contains(@class, "play-counts")]/@data-curplaycounts').get()
        post['like_counts'] = response.xpath(
            '//span[contains(@class, "like-counts")]/@data-counts').get()
        post['description'] = strip(response.xpath(
            '//p[contains(@class, "desc")]/text()').get())


        vid, = re.findall(r'vid: \"(\w+)\",',response.text)
        video_url = 'https://openapi-vtom.vmovier.com/v3/video/%s?expand=resource,resource_origin?'
        request = Request(video_url % vid,callback=self.parse_video)
        request.meta['post'] = post
        yield request

        #评论信息
        comment_url = 'http://www.xinpianchang.com/article/filmplay/ts-getCommentApi?id=%s&ajax=0&page=1'
        request = Request(comment_url % pid,callback=self.parse_comment)
        yield request

        comment_url = 'http://www.xinpianchang.com/u%s?from=articleList'
        composer_list = response.xpath('//div[@class="user-team"]//ul[@class="creator-list"]/li')
        for composer in composer_list:
            cid = composer.xpath('./a/@data-userid').get()
            request = Request(composer_url % cid, callback=self.parse_composer)
            request.meta['cid'] = cid
            yield request

            cr = CopyrightItem()
            cr['pcid'] = '%s_%s' % (cid, pid)
            cr['cid'] = cid
            cr['pid'] = pid
            cr['roles'] = composer.xpath('.//span[contains(@class,"roles")]/text()').get()
            yield cr

    def parse_video(self, response):
        post = response.meta['post']
        resp = json.loads(response.text)
        post['video'] = resp['data']['resource']['default']['url']
        post['preview'] = resp['data']['video']['cover']
        yield post

    def parse_comment(self,response):
        comments = json.loads(response.text)
        # from scrapy.shell import inspect_response  相当于断点
        # inspect_response(response,self)
        composer_url = 'http://www.xinpianchang.com/u%s?from=articleList'
        for c in comments['data']['list']:
            comment = CommentItem()
            comment['commentid'] = c['commentid']
            comment['pid'] = c['articleid']
            comment['content'] = c['content']
            comment['created_at'] = c['addtime_int']
            comment['cid'] = c['userInfo']['userid']
            comment['uname'] = c['userInfo']['username']
            comment['avatar'] = c['userInfo']['face']
            comment['like_counts'] = c['count_approve']
            if c['reply']:
               comment['reply'] = c['reply']['commentid']
            yield comment

            request = Request(composer_url % comment['cid'],callback=self.parse_composer)
            request.meta['cid'] = comment['cid']
            yield request
        #下一页
        # next_page = comments['data']['next_page_url']
        # if next_page:
        #     yield response.follow(next_page,self.parse_comment)

    def parse_composer(self, response):
        banner = response.xpath('//div[@class="banner-wrap"]/@style').get()
        composer = ComposerItem()
        composer['cid'] = response.meta['cid']
        composer['banner'] = re.findall(r'background-image:url\((.+?)\)',banner)
        composer['avatar'] = response.xpath(
            '//span[@class="avator-wrap-s"]/img/@src').get()

        composer['name'] = response.xpath(
            '//p[contains(@class, "creator-name")]/text()').get()

        composer['intro'] = response.xpath(
            '//p[contains(@class, "creator-desc")]/text()').get()

        composer['like_counts'] = ci(response.xpath(
            '//span[contains(@class, "like-counts")]/text()').get())

        composer['fans_counts'] = response.xpath(
            '//span[contains(@class, "fans-counts")]/@data-counts').get()

        composer['follow_counts'] = ci(response.xpath(
            '//span[@class="follow-wrap"]/span[2]/text()').get())

        composer['location'] = response.xpath(
            '//span[contains(@class, "icon-location")]/'
            'following-sibling::span[1]/text()').get() or ''

        composer['career'] = response.xpath(
            '//span[contains(@class, "icon-career")]/'
            'following-sibling::span[1]/text()').get() or ''
        yield composer

