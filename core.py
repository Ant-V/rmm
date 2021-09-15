import os
import sys
import subprocess
import shlex
import xml.etree.ElementTree as ET
import requests as req
import shutil
import argparse
from utils.processes import cmd_run, execute, cmd_output
from bs4 import BeautifulSoup


class Mod:
    def __init__(self, name, steamid, versions, author, fp):
        self.name = name
        self.versions = versions
        self.author = author
        self.steamid = steamid
        self.fp = fp
    def __repr__(self):
        return "<Mod name:{} author:{} steamid:{} versions:{}>"\
            .format(self.name, self.author, self.steamid, self.versions)

    def __cell__(self):
        return [self.name, self.author, self.steamid, self.versions, self.fp]

    def remove(self):
        shutil.rmtree(self.fp)

    def install(self, cache_fp):
        shutil.copytree(cache_fp, self.fp)

    @classmethod
    def create_from_path(cls, filepath):
        tree = ET.parse(filepath + "/About/About.xml")
        root = tree.getroot()
        name = root.find('name').text
        author = root.find('author').text
        versions = [v.text for v in root.find('supportedVersions').findall('li')]
        with open(filepath+"/About/PublishedFileId.txt") as f:
            steamid = f.readline().strip()

        return Mod(name, steamid, versions, author, filepath)


class ModList:
    @classmethod
    def read_text_modlist(cls, path):
        mods = []
        with open(path) as f:
            for line in f:
                itemid = line.split("#", 1)[0]
                try:
                    mods.append(int(itemid))
                except ValueError:
                    continue

        return mods

    @classmethod
    def export_text_modlist(cls, mods):
        output = ""
        for m in mods:
            output += "{}\n".format(m.steamid)

        return output

    @classmethod
    def write_text_modlist(cls, mods, path):
        with open(path, "w") as f:
            f.write(cls.export_text_modlist(mods))
              

    def install_all():
        pass

    def remove_all():
        pass


class SteamDownloader:
    @classmethod
    def download(cls, mods, folder):
        def workshop_format(mods):
            return (s := ' +workshop_download_item 294100 ') + s.join(str(x) for x in mods)
        query = "steamcmd +login anonymous +force_install_dir \"{}\" \"{}\" +quit"\
          .format(folder, workshop_format(mods))

        for line in execute(shlex.split(query)):
           print(line, end='') 

    @classmethod
    def download_modlist(cls, mods, path):
        steamids = [n.steamid for n in mods]
        return cls.download(steamids, path)

class WorkshopWebScraper:
    @classmethod
    def scrape_update_date(cls, mod):
        resp = req.get("https://steamcommunity.com/sharedfiles/filedetails/?id={}".format(mod.steamid))
        soup = BeautifulSoup(resp.content, 'html.parser')
        return list(soup.find_all('div', class_='detailsStatRight'))[2].get_text()

class Manager:
    def __init__(self, moddir):
        self.moddir = moddir

    def get_mods_list(self):
        return [ Mod.create_from_path(self.moddir + "/" + d) for d in os.listdir(self.moddir) ]

    def get_mods_names(self):
        mods = self.get_mods_list()
        table = []
        for n in mods:
            table.append(n.name)

        return table

    def backup_mod_dir(self, tarball_fp):
        query = "(cd {}; tar -vcaf \"{}\" \".\")".format(self.moddir, tarball_fp)
        for line in execute(query):
            print(line, end='')

    def remove_mod(self, mod):
        pass

    def query_mod(self):
        pass

    def update_mod(self, mod):
        pass

    def update_all_mods(self, fp):
        mods = self.get_mods_list()
        SteamDownloader().download_modlist(mods, fp) 

    def get_mod_table(self):
        from tabulate import tabulate
        return tabulate([ m.__cell__() for m in self.get_mods_list() ])

class CLI:
    def __init__(self, path=None):
        self.path = path
        parser = argparse.ArgumentParser(description='Rimworld Mod Manager (RMM)',
                                         usage='''rmm <command> [<args>]
The available commands are:
    list        List installed packages 
    update      Update all packages
    install     Installs a package or modlist 
    remove      Removes a package or modlist 
    backup      Creates an archive of the package library
    export      Saves package library state to a file
    
''')
        parser.add_argument('command', help='Subcommand to run')
        # parse_args defaults to [1:] for args, but you need to
        # exclude the rest of the args too, or validation will fail
        args = parser.parse_args(sys.argv[1:2])
        if not hasattr(self, args.command):
            print('Unrecognized command')
            parser.print_help()
            exit(1)
        # use dispatch pattern to invoke method with same name
        getattr(self, args.command)()

    def export(self):
        parser = argparse.ArgumentParser(description="Saves modlist to file.")
        parser.add_argument("filename", help="filename to write modlist to or specify '-' for stdout")
        args = parser.parse_args(sys.argv[2:])

        mods = Manager(self.path).get_mods_list()
        if (args.filename != "-"):
            ModList.write_text_modlist(mods, args.filename)
            print("Mod list written to {}.\n".format(args.filename))
        else:
            print(ModList.export_text_modlist(mods))

    def list(self):
        print(Manager(self.path).get_mod_table())

    def install(self, name):
        SteamDownloader().download_modlist(mods, "/tmp")

    def update(self):
        parser = argparse.ArgumentParser(description="Updates all mods in directory")
        parser.add_argument("filename", nargs="?", const=1, default="/tmp/rimworld")
        args = parser.parse_args(sys.argv[2:])

        print("Preparing to update following packages: " + 
              ", ".join(str(x) for x in Manager(self.path).get_mods_names()) +
              "\n\nWould you like to continue? [y/n]\n")
        
        if (input() != "y"):
            return 0

        Manager(self.path).update_all_mods(args.filename)
        print("\n\nPackage update complete.")

    def backup(self):
        parser = argparse.ArgumentParser(description="Creates a backup of the mod directory state.")
        parser.add_argument("filename", nargs="?", const=1, default="/tmp/rimworld.tar.bz2")
        args = parser.parse_args(sys.argv[2:])

        print("Backing up mod directory to '{}.\n".format(args.filename))
        Manager(self.path).backup_mod_dir(args.filename)
        print("Backup completed to " + args.filename + ".")


CLI(path="/home/miffi/apps/rimworld/game/Mods")
