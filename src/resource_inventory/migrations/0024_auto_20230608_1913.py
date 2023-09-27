# Generated by Django 2.2 on 2023-06-08 19:13

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0023_auto_20230608_1913'),
        ('booking', '0010_auto_20230608_1913'),
        ('resource_inventory', '0023_cloudinitfile_generated'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cpuprofile',
            name='host',
        ),
        migrations.RemoveField(
            model_name='diskprofile',
            name='host',
        ),
        migrations.RemoveField(
            model_name='image',
            name='from_lab',
        ),
        migrations.RemoveField(
            model_name='image',
            name='os',
        ),
        migrations.RemoveField(
            model_name='image',
            name='owner',
        ),
        migrations.RemoveField(
            model_name='installer',
            name='sup_scenarios',
        ),
        migrations.RemoveField(
            model_name='interface',
            name='acts_as',
        ),
        migrations.RemoveField(
            model_name='interface',
            name='config',
        ),
        migrations.RemoveField(
            model_name='interface',
            name='profile',
        ),
        migrations.RemoveField(
            model_name='interfaceconfiguration',
            name='connections',
        ),
        migrations.RemoveField(
            model_name='interfaceconfiguration',
            name='profile',
        ),
        migrations.RemoveField(
            model_name='interfaceconfiguration',
            name='resource_config',
        ),
        migrations.RemoveField(
            model_name='interfaceprofile',
            name='host',
        ),
        migrations.RemoveField(
            model_name='network',
            name='bundle',
        ),
        migrations.RemoveField(
            model_name='networkconnection',
            name='network',
        ),
        migrations.RemoveField(
            model_name='networkrole',
            name='network',
        ),
        migrations.RemoveField(
            model_name='opnfvconfig',
            name='installer',
        ),
        migrations.RemoveField(
            model_name='opnfvconfig',
            name='networks',
        ),
        migrations.RemoveField(
            model_name='opnfvconfig',
            name='scenario',
        ),
        migrations.RemoveField(
            model_name='opnfvconfig',
            name='template',
        ),
        migrations.RemoveField(
            model_name='opsys',
            name='from_lab',
        ),
        migrations.RemoveField(
            model_name='physicalnetwork',
            name='bundle',
        ),
        migrations.RemoveField(
            model_name='physicalnetwork',
            name='generic_network',
        ),
        migrations.RemoveField(
            model_name='ramprofile',
            name='host',
        ),
        migrations.RemoveField(
            model_name='resourcebundle',
            name='template',
        ),
        migrations.RemoveField(
            model_name='resourceconfiguration',
            name='cloud_init_files',
        ),
        migrations.RemoveField(
            model_name='resourceconfiguration',
            name='image',
        ),
        migrations.RemoveField(
            model_name='resourceconfiguration',
            name='profile',
        ),
        migrations.RemoveField(
            model_name='resourceconfiguration',
            name='template',
        ),
        migrations.RemoveField(
            model_name='resourceopnfvconfig',
            name='opnfv_config',
        ),
        migrations.RemoveField(
            model_name='resourceopnfvconfig',
            name='resource_config',
        ),
        migrations.RemoveField(
            model_name='resourceopnfvconfig',
            name='role',
        ),
        migrations.RemoveField(
            model_name='resourceprofile',
            name='labs',
        ),
        migrations.RemoveField(
            model_name='resourcetemplate',
            name='copy_of',
        ),
        migrations.RemoveField(
            model_name='resourcetemplate',
            name='lab',
        ),
        migrations.RemoveField(
            model_name='resourcetemplate',
            name='owner',
        ),
        migrations.RemoveField(
            model_name='server',
            name='bundle',
        ),
        migrations.RemoveField(
            model_name='server',
            name='config',
        ),
        migrations.RemoveField(
            model_name='server',
            name='interfaces',
        ),
        migrations.RemoveField(
            model_name='server',
            name='lab',
        ),
        migrations.RemoveField(
            model_name='server',
            name='profile',
        ),
        migrations.RemoveField(
            model_name='server',
            name='remote_management',
        ),
        migrations.RemoveField(
            model_name='vlan',
            name='network',
        ),
        migrations.DeleteModel(
            name='CloudInitFile',
        ),
        migrations.DeleteModel(
            name='CpuProfile',
        ),
        migrations.DeleteModel(
            name='DiskProfile',
        ),
        migrations.DeleteModel(
            name='Image',
        ),
        migrations.DeleteModel(
            name='Installer',
        ),
        migrations.DeleteModel(
            name='Interface',
        ),
        migrations.DeleteModel(
            name='InterfaceConfiguration',
        ),
        migrations.DeleteModel(
            name='InterfaceProfile',
        ),
        migrations.DeleteModel(
            name='Network',
        ),
        migrations.DeleteModel(
            name='NetworkConnection',
        ),
        migrations.DeleteModel(
            name='NetworkRole',
        ),
        migrations.DeleteModel(
            name='OPNFVConfig',
        ),
        migrations.DeleteModel(
            name='OPNFVRole',
        ),
        migrations.DeleteModel(
            name='Opsys',
        ),
        migrations.DeleteModel(
            name='PhysicalNetwork',
        ),
        migrations.DeleteModel(
            name='RamProfile',
        ),
        migrations.DeleteModel(
            name='RemoteInfo',
        ),
        migrations.DeleteModel(
            name='ResourceBundle',
        ),
        migrations.DeleteModel(
            name='ResourceConfiguration',
        ),
        migrations.DeleteModel(
            name='ResourceOPNFVConfig',
        ),
        migrations.DeleteModel(
            name='ResourceProfile',
        ),
        migrations.DeleteModel(
            name='ResourceTemplate',
        ),
        migrations.DeleteModel(
            name='Scenario',
        ),
        migrations.DeleteModel(
            name='Server',
        ),
        migrations.DeleteModel(
            name='Vlan',
        ),
    ]