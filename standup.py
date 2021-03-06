#!/usr/bin/env python -u
# -*- coding: utf-8 -*-
__author__ = 'Monkee Magic <magic.monkee.magic@gmail.com>'
__version__ = '0.0.1'
__license__ = 'GPLv3'
__source__ = 'http://github.com/monk-ee/diskrobiot'

"""
diskrobiot.py - A python library for disk IO testing.

Copyright (C) 2014 Lyndon Swan <magic.monkee.magic@gmail.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

Assumptions:
        if the following is true:
            iops * transfersizeinbytes = bytespersecond
        then
            iops = bytespersecond / transfersizeinbytes

    bytespersecond =

Volumes:
  Volume ###  Ltr  Label        Fs     Type        Size     Status     Info
  ----------  ---  -----------  -----  ----------  -------  ---------  --------
  Volume 0         System Rese  NTFS   Partition    350 MB  Healthy    System
  Volume 1     C                NTFS   Partition     29 GB  Healthy    Boot
* Volume 2                      RAW    Stripe        89 GB  Healthy
  Volume 4     Z   Temporary S  NTFS   Partition     37 GB  Healthy
  Volume 5     Y   Temporary S  NTFS   Partition     37 GB  Healthy
"""

import boto.ec2, boto.vpc, boto.iam, boto.cloudformation

from troposphere import Base64, Tags, GetAtt, Join
from troposphere import Output, Ref, Template
import troposphere.ec2 as ec2


class MetadataObject(object):
    def __init__(self):
        # Create the list of configs set on this object by the user
        self.configkeys = {}


    def add_configkeys(self, type, key, item, data):
        if type not in self.configkeys:
            self.configkeys[type] = {}
            self.configkeys[type][key] = {}
            self.configkeys[type][key][item] = data
        else:
            if key not in self.configkeys[type]:
                self.configkeys[type][key] = {}
                self.configkeys[type][key][item] = data
            else:
                if item not in self.configkeys[type][key]:
                    self.configkeys[type][key][item] = data
                else:
                    self.configkeys[type][key][item].update(data)

    def JSONrepr(self):
        return self.configkeys


class StandUp:
    region = "ap-southeast-2"
    subnet = "subnet-cb5facae"
    type = "m3.xlarge"
    ami = "ami-e95c31d3"
    stackname = "TestIOStack"
    name = "windows-2012-test"
    instance_template = "TestIO"
    timezone = "Australia/Brisbane"
    environment = "Development"
    comment = "Comments"
    keypair = "IOTEST"
    iamrole = "IAM-EC2-Default"
    securitygroups = ["sg-02b36667"]
    monitoring = False
    rollback = False
    volume = ""
    ec2conn = ""
    cfnconn = ""
    template = ""

    def __init__(self):
        self.build()
        self.output_to_file()

    def output_to_file(self):
        output = self.template.to_json()
        fd =  open('standup.json', 'w')
        fd.write(output)
        fd.close()
        print(output)

    def metadata(self):
        m = MetadataObject()

        m.add_configkeys('AWS::CloudFormation::Init', 'InitRAID', 'files', {
            "C:\\cfn\\scripts\\striperaidebs.txt": {
                "content": """select disk 1
                            clean
                            convert dynamic
                            select disk 2
                            clean
                            convert dynamic
                            create volume stripe disk=1,2
                            list volume
                            select volume 2
                            assign letter=e
                            format fs=ntfs quick"""
            },
            "C:\\cfn\\scripts\\striperaidephemeral.txt": {
                "content": """select disk 2
                            clean
                            convert dynamic
                            select disk 3
                            clean
                            convert dynamic
                            create volume stripe disk=2,3
                            select volume 2
                            assign letter=E
                            format fs=ntfs quick"""
            }
        }
        )
        m.add_configkeys('AWS::CloudFormation::Init', 'InitRAID', 'commands', {
            "1-initialize-raid-1": {
                "command": """diskpart /s C:\\cfn\\scripts\\striperaidebs.txt""",
                "waitAfterCompletion": 0
            }
        }
        )
        m.add_configkeys('AWS::CloudFormation::Init', 'TestIO', 'packages', {
                "msi": {
                    "python": """https://www.python.org/ftp/python/3.4.2/python-3.4.2.amd64.msi"""
                }
            }
        )
        m.add_configkeys('AWS::CloudFormation::Init', 'TestIO', 'files', {
            "C:\\cfn\\scripts\\DiskRobIOt.py":
                """https://raw.githubusercontent.com/monk-ee/DiskRobIOt/master/DiskRobIOt.py"""
        }
        )
        m.add_configkeys('AWS::CloudFormation::Init', 'TestIO', 'commands', {
                "1-python-path": {
                    "command": """setx path "%path%;C:\\Python34" """,
                    "waitAfterCompletion": 0
                },
                "2-run-disktest": {
                    "command": """c:\\cfn\\scripts\DiskRobIOt.py --path e:\\ """,
                    "waitAfterCompletion": 0
                }
            }
        )
        m.add_configkeys('AWS::CloudFormation::Init', 'configSets', 'config',
                         ["InitRAID", "TestIO"]
        )
        return m

    def build(self):
        self.template = Template()
        self.template.add_version()
        self.template.add_description(self.comment)
        m = self.metadata()
        ec2_instance = self.template.add_resource(ec2.Instance(
            self.instance_template,
            ImageId=self.ami,
            InstanceType=self.type,
            KeyName=self.keypair,
            SubnetId=self.subnet,
            SecurityGroupIds=self.securitygroups,
            Monitoring=self.monitoring,
            IamInstanceProfile=self.iamrole,
            UserData=Base64("""<script> cfn-init -v -s  """ + self.stackname + """ -r """ + self.instance_template + """  --region """ + self.region + """  --configset config</script>"""),
            Metadata=m.JSONrepr(),
            BlockDeviceMappings=[
                ec2.BlockDeviceMapping(
                    DeviceName="/dev/xvdca",
                    VirtualName="ephemeral0",
                ),
                ec2.BlockDeviceMapping(
                    DeviceName="/dev/xvdcb",
                    VirtualName="ephemeral1",
                ),
                ec2.BlockDeviceMapping(
                    DeviceName="/dev/xvdb",
                    Ebs=ec2.EBSBlockDevice(
                        DeleteOnTermination=True,
                        VolumeSize="45",
                        VolumeType="gp2"
                    ),
                ),
                ec2.BlockDeviceMapping(
                    DeviceName="/dev/xvdc",
                    Ebs=ec2.EBSBlockDevice(
                        DeleteOnTermination=True,
                        VolumeSize="45",
                        VolumeType="gp2"
                    ),
                )
            ],
            Tags=Tags(
                Name=self.name,
                Environment=self.environment,
                Comment=self.comment,
                Role=self.iamrole,
            ),
        ))

        self.template.add_resource(ec2.EIP(
            "EIP",
            InstanceId=Ref(ec2_instance),
            Domain='vpc',
        ))

        self.template.add_output([
            Output(
                "InstanceId",
                Description="InstanceId of the newly created EC2 instance",
                Value=Ref(ec2_instance),
            ),
            Output(
                "PrivateIP",
                Description="Private IP address of the newly created EC2 instance",
                Value=GetAtt(ec2_instance, "PrivateIp"),
            ),
            Output(
                "PrivateDNS",
                Description="Private DNSName of the newly created EC2 instance",
                Value=GetAtt(ec2_instance, "PrivateDnsName"),
            )
        ])


    def cloudform(self):
        try:
            self.cfnconn.create_stack(self.stackname, template_body=self.template.to_json(),
                                      disable_rollback=self.rollback)
            output = self.template.to_json()
            return output
        except Exception as e:
            raise

    def ec2_connect_to_region(self):
        try:
            self.ec2conn = boto.ec2.connect_to_region(self.region)
        except:
            raise


    def vpc_connect_to_region(self):
        try:
            self.vpcconn = boto.vpc.connect_to_region(self.region)
        except:
            raise


    def iam_connect_to_region(self):
        try:
            self.iamconn = boto.iam.connect_to_region(self.region)
        except:
            raise


    def cfn_connect_to_region(self):
        try:
            self.cfnconn = boto.cloudformation.connect_to_region(self.region)
        except:
            raise


if __name__ == '__main__':
    sup = StandUp()