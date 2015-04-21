#!/usr/bin/env python
import json, pickle, argparse
from urllib.request import urlopen
from urllib.parse import urlunparse, urlencode
from urllib.error import HTTPError
from config import API_KEY
import os



class LoadException(Exception):
    def __init__(self, status, message='Error',):
        self.message = message
        self.status = status
        super(LoadException, self).__init__()

    def __str__(self):
        return self.message + '{}'.format(self.status)


class TumblrDL:

    def __init__(self, blog, last_id=None):
        self.blog = blog
        self.img_path = blog.replace('.', '_')
        self.status_file = os.path.join(self.img_path, 'status')
        self.status = {'img_links':[], 'cur_post_num':0,
                       'broken_img_links':[]}
        # check if path dor downloads exists
        if not os.path.exists(self.img_path):
            os.mkdir(self.img_path)
        elif not os.path.isdir(self.img_path):
            # remove image path if it is file
            # and create image path directory
            os.remove(self.img_path)
            os.mkdir(self.img_path)
        else:
            if os.path.exists(self.status_file):
                with open(self.status_file, 'r+b') as status_file:
                    self.status = pickle.load(status_file)
        # self.img_links = []
        # self.posts_count = None
        # self.cur_post_number = 1
        # self.last_id = last_id

    def build_url(self):
        query = {'api_key':API_KEY, 'limit':5}
        if self.status.get('last_id', None):
            query['before_id'] = self.status['last_id']
        query = urlencode(query)
        path = '/v2/blog/{}/posts/photo'.format(self.blog)
        url = urlunparse(('http',           # scheme
                          'api.tumblr.com', # netloc
                          path,             # path
                          '',               # params
                          query,            # query
                          ''))              # anchor
        return url

    @classmethod
    def load_resource(cls, url):
        resp = urlopen(url)
        return resp.read()

    def save_progress(self):
        with open(self.status_file, 'w+b') as status_file:
            pickle.dump(self.status, status_file)

    def collect_links(self):
        url = self.build_url()
        resp = self.load_resource(url)
        resp_json = json.loads(resp.decode())

        self.status['last_status'] = resp_json['meta']['status']
        resp = resp_json['response']
        if not self.status.get('total_posts', None):
            self.status['total_posts'] = resp['total_posts']
        # get posts from response
        posts = resp['posts']
        # check whether all posts already loaded
        if len(posts) == 0 or \
           self.status.get('cur_post_num') == \
           self.status.get('total_posts'):
            self.status['collect_status'] = 'OK'
            print('Collecting links is done')
        for post in posts:
            self.status['last_id'] = post['id']
            self.status['cur_post_num'] += 1
            print('{} of {} post id: {}'.\
                  format(self.status['cur_post_num'],
                         self.status['total_posts'],
                         self.status['last_id']))
            for photo in post['photos']:
                link = photo['original_size']['url']
                self.status['img_links'].append(link)
        self.save_progress()

    def load_image(self):
        while self.status['img_links']:
            link = self.status['img_links'].pop()
            try:
                print('{} Open image: {}'.format(
                    len(self.status['img_links']), link), end=' ')
                res = self.load_resource(link)
                print('DONE')
                filename = os.path.join(
                    self.img_path, link.rsplit('/', 1)[-1])
                with open(filename, 'w+b') as img_file:
                    img_file.write(res)
            except HTTPError as error:
                print('ERROR', error.code, error.reason)
                self.status['broken_img_links'].append(link)

    def get_images(self):
        while self.status.get('collect_status') != 'OK':
            self.collect_links()
        self.load_image()
        if self.status['broken_img_links']:
            print('Some files did not loaded')
        else:
            print('All files loaded')
            os.remove(self.status_file)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('blog', help='tumblr blog like "someblog.tumblr.com')
    args = parser.parse_args()
    loader = TumblrDL(args.blog)
    loader.get_images()


if __name__ == '__main__':
    main()
