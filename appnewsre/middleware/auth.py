from django.http import HttpResponseRedirect, HttpResponse
from django.middleware.common import CommonMiddleware
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin


class AuthMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.path_info == "/login/":
            return
        if request.path_info == "/user_register/":
            return
        if request.path_info == "/register/":
            return
        # 读取当前访问的用户的session信息，如果能读到，说明已登录过，就可以继续向后走
        info_dict = request.session.get('info')
        print(info_dict)
        if info_dict:
            return

        # 没有登录过
        return redirect('/login/')
