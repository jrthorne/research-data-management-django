from django.db import models

# Create your models here.
class Server(models.Model):
    name            = models.CharField(max_length=255)
    domain          = models.CharField(max_length=255, blank=True)
    ip              = models.GenericIPAddressField(null=True, blank=True)
    description     = models.TextField(blank=True)
    
    def __unicode__(self):
        return self.name
    # end unicode
    
    def status(self):
        return True
    # end status
    status.boolean = True
# end Server

class Check(models.Model):
    server          = models.ForeignKey('Server')
    name            = models.CharField(max_length=255, blank=True)
    command         = models.CharField(max_length=255, blank=True)
    performed       = models.DateTimeField(auto_now=True)
    returned_value  = models.TextField()
    
    def __unicode__(self):
        return self.server.name + "-" + self.performed.strftime("%d %h %Y")
    # end unicode
# end check
    
    
