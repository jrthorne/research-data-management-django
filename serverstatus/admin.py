from django.contrib import admin
from models import *

class ServerAdmin(admin.ModelAdmin):
    list_display = ['name', 'status']
# end ServerAdmin

# Register your models here.
admin.site.register(Server, ServerAdmin)
admin.site.register(Check)
