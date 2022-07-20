﻿# This file is part of Tautulli.
#
#  Tautulli is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Tautulli is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Tautulli.  If not, see <http://www.gnu.org/licenses/>.

import datetime
from time import mktime

import plexpy
from plexpy import common
from plexpy import database
from plexpy import logger
from plexpy import session


class Graphs(object):

    def __init__(self):
        pass

    def get_total_plays_per_day(self, time_range='30', x_axis='media', y_axis='plays', server_id=None, user_id=None, grouping=None):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'
        
        if server_id and server_id.isdigit():
            server_cond = 'AND session_history.server_id = %s ' % server_id
            server_cond2 = 'WHERE id = %s ' % server_id
        elif session.get_session_shared_servers():
            allowed_servers = ','.join(session.get_session_shared_servers())
            server_cond = 'AND session_history.server_id IN (%s) ' % allowed_servers
            server_cond2 = 'WHERE id IN (%s) ' % allowed_servers
        else:
            server_cond = ''
            server_cond2 = ''

        user_cond = ''
        if session.get_session_user_id() and user_id and user_id != str(session.get_session_user_id()):
            user_cond = 'AND session_history.user_id = %s ' % session.get_session_user_id()
        elif user_id and user_id.isdigit():
            user_cond = 'AND session_history.user_id = %s ' % user_id

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        group_by = 'reference_id' if grouping else 'id'

        try:
            if x_axis == 'media' and y_axis == 'plays':
                data = {'tv_count': {'label': 'TV', 'series': []},
                        'movie_count': {'label': 'Movies', 'series': []},
                        'music_count': {'label': 'Music', 'series': []},
                        }
                query = 'SELECT date(started, "unixepoch", "localtime") AS date_played, ' \
                        'SUM(CASE WHEN media_type = "episode" THEN 1 ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "movie" THEN 1 ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "track" THEN 1 ELSE 0 END) AS music_count ' \
                        'FROM (SELECT * FROM session_history ' \
                        'GROUP BY date(started, "unixepoch", "localtime"), %s) ' \
                        'AS session_history ' \
                        'WHERE datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") %s %s' \
                        'GROUP BY date_played ' \
                        'ORDER BY date_played ASC' % (group_by, time_range, server_cond, user_cond)

                result = monitor_db.select(query)

            elif x_axis == 'media' and y_axis == 'duration':
                data = {'tv_count': {'label': 'TV', 'series': []},
                        'movie_count': {'label': 'Movies', 'series': []},
                        'music_count': {'label': 'Music', 'series': []},
                        }
                query = 'SELECT date(started, "unixepoch", "localtime") AS date_played, ' \
                        'SUM(CASE WHEN media_type = "episode" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS TV, ' \
                        'SUM(CASE WHEN media_type = "movie" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS Movies, ' \
                        'SUM(CASE WHEN media_type = "track" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS Music ' \
                        'FROM session_history ' \
                        'WHERE datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") %s %s' \
                        'GROUP BY date_played ' \
                        'ORDER BY date_played ASC' % (time_range, server_cond, user_cond)

                result = monitor_db.select(query)

            elif x_axis == 'server' and y_axis == 'plays':
                query = 'SELECT id, pms_name FROM servers %s ORDER BY pms_name' % server_cond2
                servers = monitor_db.select(query)
                columns = ''
                data = {}
                cnt = 0
                for server in servers:
                    columns += 'SUM(CASE WHEN server_id = %s THEN 1 ELSE 0 END) AS %s, ' % (
                        server['id'], "'" + str(cnt) + "'")
                    data[str(cnt)] = {'label': server['pms_name'], 'series': []}
                    cnt += 1
                columns = columns.rstrip(', ')

                query = 'SELECT date(started, "unixepoch", "localtime") AS date_played, ' \
                        '%s ' \
                        'FROM (SELECT * FROM session_history ' \
                        'GROUP BY date(started, "unixepoch", "localtime"), %s) ' \
                        'AS session_history ' \
                        'WHERE datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") %s %s' \
                        'GROUP BY date_played ' \
                        'ORDER BY date_played ASC' % (columns, group_by, time_range, server_cond, user_cond)

                result = monitor_db.select(query)

            elif x_axis == 'server' and y_axis == 'duration':
                query = 'SELECT id, pms_name FROM servers %s ORDER BY pms_name' % server_cond2
                servers = monitor_db.select(query)
                columns = ''
                data = {}
                cnt = 0
                for server in servers:
                    columns += 'SUM(CASE WHEN server_id = %s AND stopped > 0 THEN (stopped - started) ' \
                               '- (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS %s, ' \
                               % (server['id'], "'" + str(cnt) + "'")
                    data[str(cnt)] = {'label': server['pms_name'], 'series': []}
                    cnt += 1
                columns = columns.rstrip(', ')

                query = 'SELECT date(started, "unixepoch", "localtime") AS date_played, ' \
                        ' %s ' \
                        'FROM session_history ' \
                        'WHERE datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") %s %s' \
                        'GROUP BY date_played ' \
                        'ORDER BY date_played ASC' % (columns, time_range, server_cond, user_cond)

                result = monitor_db.select(query)

        except Exception as e:
            logger.warn(u"Tautulli Graphs :: Unable to execute database query for get_total_plays_per_day: %s." % e)
            return None

        # create our date range as some days may not have any data
        # but we still want to display them
        base = datetime.date.today()
        start_date = base - datetime.timedelta(days=int(time_range)-1)

        for col in data.keys():
            data[col]['series'] = [0 for x in range(0, int(time_range))]

        categories = []
        for x in range(0, int(time_range)):
            d = start_date + datetime.timedelta(days=x)
            categories.append(d.strftime('%Y-%m-%d'))

        for item in result:
            delta = datetime.datetime.strptime(item['date_played'], '%Y-%m-%d').date() - start_date
            offset = delta.days
            if offset >= 0:
                for col in data.keys():
                    data[col]['series'][offset] = item[col]

        output = {'categories': categories,
                  'series': [],
                  }
        for col in sorted(data.keys()):
            output['series'].append({'data': data[col]['series'], 'name': data[col]['label']})

        return output

    def get_total_plays_per_dayofweek(self, time_range='30', x_axis='media', y_axis='plays', server_id=None, user_id=None, grouping=None):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'

        if server_id and server_id.isdigit():
            server_cond = 'AND session_history.server_id = %s ' % server_id
            server_cond2 = 'WHERE id = %s ' % server_id
        elif session.get_session_shared_servers():
            allowed_servers = ','.join(session.get_session_shared_servers())
            server_cond = 'AND session_history.server_id IN (%s) ' % allowed_servers
            server_cond2 = 'WHERE id IN (%s) ' % allowed_servers
        else:
            server_cond = ''
            server_cond2 = ''

        user_cond = ''
        if session.get_session_user_id() and user_id and user_id != str(session.get_session_user_id()):
            user_cond = 'AND session_history.user_id = %s ' % session.get_session_user_id()
        elif user_id and user_id.isdigit():
            user_cond = 'AND session_history.user_id = %s ' % user_id

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        group_by = 'reference_id' if grouping else 'id'

        try:
            if x_axis == 'media' and y_axis == 'plays':
                data = {'tv_count': {'label': 'TV', 'series': []},
                        'movie_count': {'label': 'Movies', 'series': []},
                        'music_count': {'label': 'Music', 'series': []},
                        }
                query = 'SELECT strftime("%%w", datetime(started, "unixepoch", "localtime")) AS daynumber, ' \
                        '(CASE CAST(strftime("%%w", datetime(started, "unixepoch", "localtime")) AS INTEGER) ' \
                        'WHEN 0 THEN "Sunday" ' \
                        'WHEN 1 THEN "Monday" ' \
                        'WHEN 2 THEN "Tuesday" ' \
                        'WHEN 3 THEN "Wednesday" ' \
                        'WHEN 4 THEN "Thursday" ' \
                        'WHEN 5 THEN "Friday" ' \
                        'ELSE "Saturday" END) AS dayofweek, ' \
                        'SUM(CASE WHEN media_type = "episode" THEN 1 ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "movie" THEN 1 ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "track" THEN 1 ELSE 0 END) AS music_count ' \
                        'FROM (SELECT * FROM session_history ' \
                        'GROUP BY strftime("%%w", datetime(started, "unixepoch", "localtime")), %s) ' \
                        'AS session_history ' \
                        'WHERE datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") %s %s' \
                        'GROUP BY dayofweek ' \
                        'ORDER BY daynumber' % (group_by, time_range, server_cond, user_cond)

                result = monitor_db.select(query)

            elif x_axis == 'media' and y_axis == 'duration':
                data = {'tv_count': {'label': 'TV', 'series': []},
                        'movie_count': {'label': 'Movies', 'series': []},
                        'music_count': {'label': 'Music', 'series': []},
                        }
                query = 'SELECT strftime("%%w", datetime(started, "unixepoch", "localtime")) AS daynumber, ' \
                        '(CASE CAST(strftime("%%w", datetime(started, "unixepoch", "localtime")) AS INTEGER) ' \
                        'WHEN 0 THEN "Sunday" ' \
                        'WHEN 1 THEN "Monday" ' \
                        'WHEN 2 THEN "Tuesday" ' \
                        'WHEN 3 THEN "Wednesday" ' \
                        'WHEN 4 THEN "Thursday" ' \
                        'WHEN 5 THEN "Friday" ' \
                        'ELSE "Saturday" END) AS dayofweek, ' \
                        'SUM(CASE WHEN media_type = "episode" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "movie" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "track" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS music_count ' \
                        'FROM session_history ' \
                        'WHERE datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") %s %s' \
                        'GROUP BY dayofweek ' \
                        'ORDER BY daynumber' % (time_range, server_cond, user_cond)

                result = monitor_db.select(query)

            elif x_axis == 'server' and y_axis == 'plays':
                query = 'SELECT id, pms_name FROM servers %s ORDER BY pms_name' % server_cond2
                servers = monitor_db.select(query)
                columns = ''
                data = {}
                cnt = 0
                for server in servers:
                    columns += 'SUM(CASE WHEN server_id = %s THEN 1 ELSE 0 END) AS %s, ' % (
                        server['id'], "'" + str(cnt) + "'")
                    data[str(cnt)] = {'label': server['pms_name'], 'series': []}
                    cnt += 1
                columns = columns.rstrip(', ')

                query = 'SELECT strftime("%%w", datetime(started, "unixepoch", "localtime")) AS daynumber, ' \
                        '(CASE CAST(strftime("%%w", datetime(started, "unixepoch", "localtime")) AS INTEGER) ' \
                        'WHEN 0 THEN "Sunday" ' \
                        'WHEN 1 THEN "Monday" ' \
                        'WHEN 2 THEN "Tuesday" ' \
                        'WHEN 3 THEN "Wednesday" ' \
                        'WHEN 4 THEN "Thursday" ' \
                        'WHEN 5 THEN "Friday" ' \
                        'ELSE "Saturday" END) AS dayofweek, ' \
                        '%s ' \
                        'FROM (SELECT * FROM session_history ' \
                        'GROUP BY strftime("%%w", datetime(started, "unixepoch", "localtime")), %s) ' \
                        'AS session_history ' \
                        'WHERE datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") %s %s' \
                        'GROUP BY dayofweek ' \
                        'ORDER BY daynumber' % (columns, group_by, time_range, server_cond, user_cond)

                result = monitor_db.select(query)

            elif x_axis == 'server' and y_axis == 'duration':
                query = 'SELECT id, pms_name FROM servers %s ORDER BY pms_name' % server_cond2
                servers = monitor_db.select(query)
                columns = ''
                data = {}
                cnt = 0
                for server in servers:
                    columns += 'SUM(CASE WHEN server_id = %s AND stopped > 0 THEN (stopped - started) ' \
                               '- (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS %s, ' \
                               % (server['id'], "'" + str(cnt) + "'")
                    data[str(cnt)] = {'label': server['pms_name'], 'series': []}
                    cnt += 1
                columns = columns.rstrip(', ')

                query = 'SELECT strftime("%%w", datetime(started, "unixepoch", "localtime")) AS daynumber, ' \
                        '(CASE CAST(strftime("%%w", datetime(started, "unixepoch", "localtime")) AS INTEGER) ' \
                        'WHEN 0 THEN "Sunday" ' \
                        'WHEN 1 THEN "Monday" ' \
                        'WHEN 2 THEN "Tuesday" ' \
                        'WHEN 3 THEN "Wednesday" ' \
                        'WHEN 4 THEN "Thursday" ' \
                        'WHEN 5 THEN "Friday" ' \
                        'ELSE "Saturday" END) AS dayofweek, ' \
                        '%s ' \
                        'FROM session_history ' \
                        'WHERE datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") %s %s' \
                        'GROUP BY dayofweek ' \
                        'ORDER BY daynumber' % (columns, time_range, server_cond, user_cond)

                result = monitor_db.select(query)


        except Exception as e:
            logger.warn(u"Tautulli Graphs :: Unable to execute database query for get_total_plays_per_dayofweek: %s." % e)
            return None

        if plexpy.CONFIG.WEEK_START_MONDAY:
            days_list = ['Monday', 'Tuesday', 'Wednesday',
                         'Thursday', 'Friday', 'Saturday', 'Sunday']
            for item in result:
                if item['daynumber'] == "0":
                    item['daynumber'] = "6"
                else:
                    item['daynumber'] = str(int(item['daynumber']) - 1)
        else:
            days_list = ['Sunday', 'Monday', 'Tuesday', 'Wednesday',
                         'Thursday', 'Friday', 'Saturday']

        for col in data.keys():
            data[col]['series'] = [0 for x in days_list]

        categories = []
        for day_item in days_list:
            categories.append(day_item)

        for item in result:
            offset = int(item['daynumber'])
            for col in data.keys():
                data[col]['series'][offset] = item[col]

        output = {'categories': categories,
                  'series': [],
                  }
        for col in sorted(data.keys()):
            output['series'].append({'data': data[col]['series'], 'name': data[col]['label']})

        return output

    def get_total_plays_per_hourofday(self, time_range='30', x_axis='media', y_axis='plays', server_id=None, user_id=None, grouping=None):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'

        if server_id and server_id.isdigit():
            server_cond = 'AND session_history.server_id = %s ' % server_id
            server_cond2 = 'WHERE id = %s ' % server_id
        elif session.get_session_shared_servers():
            allowed_servers = ','.join(session.get_session_shared_servers())
            server_cond = 'AND session_history.server_id IN (%s) ' % allowed_servers
            server_cond2 = 'WHERE id IN (%s) ' % allowed_servers
        else:
            server_cond = ''
            server_cond2 = ''

        user_cond = ''
        if session.get_session_user_id() and user_id and user_id != str(session.get_session_user_id()):
            user_cond = 'AND session_history.user_id = %s ' % session.get_session_user_id()
        elif user_id and user_id.isdigit():
            user_cond = 'AND session_history.user_id = %s ' % user_id

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        group_by = 'reference_id' if grouping else 'id'

        try:
            if x_axis == 'media' and y_axis == 'plays':
                data = {'tv_count': {'label': 'TV', 'series': []},
                        'movie_count': {'label': 'Movies', 'series': []},
                        'music_count': {'label': 'Music', 'series': []},
                        }
                query = 'SELECT strftime("%%H", datetime(started, "unixepoch", "localtime")) AS hourofday, ' \
                        'SUM(CASE WHEN media_type = "episode" THEN 1 ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "movie" THEN 1 ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "track" THEN 1 ELSE 0 END) AS music_count ' \
                        'FROM (SELECT * FROM session_history ' \
                        'GROUP BY strftime("%%H", datetime(started, "unixepoch", "localtime")) , %s) ' \
                        'AS session_history ' \
                        'WHERE datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") %s %s' \
                        'GROUP BY hourofday ' \
                        'ORDER BY hourofday' % (group_by, time_range, server_cond, user_cond)

                result = monitor_db.select(query)

            elif x_axis == 'media' and y_axis == 'duration':
                data = {'tv_count': {'label': 'TV', 'series': []},
                        'movie_count': {'label': 'Movies', 'series': []},
                        'music_count': {'label': 'Music', 'series': []},
                        }
                query = 'SELECT strftime("%%H", datetime(started, "unixepoch", "localtime")) AS hourofday, ' \
                        'SUM(CASE WHEN media_type = "episode" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "movie" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "track" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS music_count ' \
                        'FROM session_history ' \
                        'WHERE datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") %s %s' \
                        'GROUP BY hourofday ' \
                        'ORDER BY hourofday' % (time_range, server_cond, user_cond)

                result = monitor_db.select(query)

            elif x_axis == 'server' and y_axis == 'plays':
                query = 'SELECT id, pms_name FROM servers %s ORDER BY pms_name' % server_cond2
                servers = monitor_db.select(query)
                columns = ''
                data = {}
                cnt = 0
                for server in servers:
                    columns += 'SUM(CASE WHEN server_id = %s THEN 1 ELSE 0 END) AS %s, ' % (
                        server['id'], "'" + str(cnt) + "'")
                    data[str(cnt)] = {'label': server['pms_name'], 'series': []}
                    cnt += 1
                columns = columns.rstrip(', ')

                query = 'SELECT strftime("%%H", datetime(started, "unixepoch", "localtime")) AS hourofday, ' \
                        '%s ' \
                        'FROM (SELECT * FROM session_history ' \
                        'GROUP BY strftime("%%H", datetime(started, "unixepoch", "localtime")) , %s) ' \
                        'AS session_history ' \
                        'WHERE datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") %s %s' \
                        'GROUP BY hourofday ' \
                        'ORDER BY hourofday' % (columns, group_by, time_range, server_cond, user_cond)

                result = monitor_db.select(query)

            elif x_axis == 'server' and y_axis == 'duration':
                query = 'SELECT id, pms_name FROM servers %s ORDER BY pms_name' % server_cond2
                servers = monitor_db.select(query)
                columns = ''
                data = {}
                cnt = 0
                for server in servers:
                    columns += 'SUM(CASE WHEN server_id = %s AND stopped > 0 THEN (stopped - started) ' \
                               '- (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS %s, ' \
                               % (server['id'], "'" + str(cnt) + "'")
                    data[str(cnt)] = {'label': server['pms_name'], 'series': []}
                    cnt += 1
                columns = columns.rstrip(', ')

                query = 'SELECT strftime("%%H", datetime(started, "unixepoch", "localtime")) AS hourofday, ' \
                        '%s ' \
                        'FROM session_history ' \
                        'WHERE datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") %s %s' \
                        'GROUP BY hourofday ' \
                        'ORDER BY hourofday' % (columns, time_range, server_cond, user_cond)

                result = monitor_db.select(query)

        except Exception as e:
            logger.warn(u"Tautulli Graphs :: Unable to execute database query for get_total_plays_per_hourofday: %s." % e)
            return None

        hours_list = ['00','01','02','03','04','05',
                      '06','07','08','09','10','11',
                      '12','13','14','15','16','17',
                      '18','19','20','21','22','23']

        for col in data.keys():
            data[col]['series'] = [0 for x in hours_list]

        categories = []
        for hour_item in hours_list:
            categories.append(hour_item)

        for item in result:
            offset = int(item['hourofday'])
            for col in data.keys():
                data[col]['series'][offset] = item[col]

        output = {'categories': categories,
                  'series': [],
                  }
        for col in sorted(data.keys()):
            output['series'].append({'data': data[col]['series'], 'name': data[col]['label']})

        return output

    def get_total_plays_per_month(self, time_range='12', x_axis='media', y_axis='plays', server_id=None, user_id=None, grouping=None):
        import time as time

        if not time_range.isdigit():
            time_range = '12'

        monitor_db = database.MonitorDatabase()

        if server_id and server_id.isdigit():
            server_cond = 'AND session_history.server_id = %s ' % server_id
            server_cond2 = 'WHERE id = %s ' % server_id
        elif session.get_session_shared_servers():
            allowed_servers = ','.join(session.get_session_shared_servers())
            server_cond = 'AND session_history.server_id IN (%s) ' % allowed_servers
            server_cond2 = 'WHERE id IN (%s) ' % allowed_servers
        else:
            server_cond = ''
            server_cond2 = ''

        user_cond = ''
        if session.get_session_user_id() and user_id and user_id != str(session.get_session_user_id()):
            user_cond = 'AND session_history.user_id = %s ' % session.get_session_user_id()
        elif user_id and user_id.isdigit():
            user_cond = 'AND session_history.user_id = %s ' % user_id

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        group_by = 'reference_id' if grouping else 'id'

        try:
            if x_axis == 'media' and y_axis == 'plays':
                data = {'tv_count': {'label': 'TV', 'series': []},
                        'movie_count': {'label': 'Movies', 'series': []},
                        'music_count': {'label': 'Music', 'series': []},
                        }
                query = 'SELECT strftime("%%Y-%%m", datetime(started, "unixepoch", "localtime")) AS datestring, ' \
                        'SUM(CASE WHEN media_type = "episode" THEN 1 ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "movie" THEN 1 ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "track" THEN 1 ELSE 0 END) AS music_count ' \
                        'FROM (SELECT * FROM session_history ' \
                        'GROUP BY strftime("%%Y-%%m", datetime(started, "unixepoch", "localtime")), %s) ' \
                        'AS session_history ' \
                        'WHERE datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s months", "localtime") %s %s' \
                        'GROUP BY strftime("%%Y-%%m", datetime(started, "unixepoch", "localtime")) ' \
                        'ORDER BY datestring DESC LIMIT %s' % (group_by, time_range, server_cond, user_cond, time_range)

                result = monitor_db.select(query)

            elif x_axis == 'media' and y_axis == 'duration':
                data = {'tv_count': {'label': 'TV', 'series': []},
                        'movie_count': {'label': 'Movies', 'series': []},
                        'music_count': {'label': 'Music', 'series': []},
                        }
                query = 'SELECT strftime("%%Y-%%m", datetime(started, "unixepoch", "localtime")) AS datestring, ' \
                        'SUM(CASE WHEN media_type = "episode" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "movie" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "track" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS music_count ' \
                        'FROM session_history ' \
                        'WHERE datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s months", "localtime") %s %s' \
                        'GROUP BY strftime("%%Y-%%m", datetime(started, "unixepoch", "localtime")) ' \
                        'ORDER BY datestring DESC LIMIT %s' % (time_range, server_cond, user_cond, time_range)

                result = monitor_db.select(query)

            elif x_axis == 'server' and y_axis == 'plays':
                query = 'SELECT id, pms_name FROM servers %s ORDER BY pms_name' % server_cond2
                servers = monitor_db.select(query)
                columns = ''
                data = {}
                cnt = 0
                for server in servers:
                    columns += 'SUM(CASE WHEN server_id = %s THEN 1 ELSE 0 END) AS %s, ' % (
                        server['id'], "'" + str(cnt) + "'")
                    data[str(cnt)] = {'label': server['pms_name'], 'series': []}
                    cnt += 1
                columns = columns.rstrip(', ')

                query = 'SELECT strftime("%%Y-%%m", datetime(started, "unixepoch", "localtime")) AS datestring, ' \
                        '%s ' \
                        'FROM (SELECT * FROM session_history ' \
                        'GROUP BY strftime("%%Y-%%m", datetime(started, "unixepoch", "localtime")), %s) ' \
                        'AS session_history ' \
                        'WHERE datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s months", "localtime") %s %s' \
                        'GROUP BY strftime("%%Y-%%m", datetime(started, "unixepoch", "localtime")) ' \
                        'ORDER BY datestring DESC LIMIT %s' % (columns, group_by, time_range, server_cond, user_cond, time_range)

                result = monitor_db.select(query)

            elif x_axis == 'server' and y_axis == 'duration':
                query = 'SELECT id, pms_name FROM servers %s ORDER BY pms_name' % server_cond2
                servers = monitor_db.select(query)
                columns = ''
                data = {}
                cnt = 0
                for server in servers:
                    columns += 'SUM(CASE WHEN server_id = %s AND stopped > 0 THEN (stopped - started) ' \
                               '- (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS %s, ' \
                               % (server['id'], "'" + str(cnt) + "'")
                    data[str(cnt)] = {'label': server['pms_name'], 'series': []}
                    cnt += 1
                columns = columns.rstrip(', ')

                query = 'SELECT strftime("%%Y-%%m", datetime(started, "unixepoch", "localtime")) AS datestring, ' \
                        '%s ' \
                        'FROM session_history ' \
                        'WHERE datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s months", "localtime") %s %s' \
                        'GROUP BY strftime("%%Y-%%m", datetime(started, "unixepoch", "localtime")) ' \
                        'ORDER BY datestring DESC LIMIT %s' % (columns, time_range, server_cond, user_cond, time_range)

                result = monitor_db.select(query)

        except Exception as e:
            logger.warn(u"Tautulli Graphs :: Unable to execute database query for get_total_plays_per_month: %s." % e)
            return None

        # create our date range as some months may not have any data
        # but we still want to display them
        base = time.localtime()
        month_range = [time.localtime(
            time.mktime((base.tm_year, base.tm_mon - n, 1, 0, 0, 0, 0, 0, 0))) for n in range(int(time_range))]

        sm = time.localtime(time.mktime((base.tm_year, base.tm_mon - int(time_range) + 1, 1, 0, 0, 0, 0, 0, 0)))
        start_month = datetime.datetime.fromtimestamp(mktime(sm))

        for col in data.keys():
            data[col]['series'] = [0 for x in month_range]

        categories = []
        for month_item in sorted(month_range):
            dt = datetime.datetime(*month_item[:6])
            date_string = dt.strftime('%Y-%m')
            categories.append(dt.strftime('%b %Y'))

        for item in result:
            offset = (datetime.datetime.strptime(item['datestring'], '%Y-%m').year * 12 + datetime.datetime.strptime(item['datestring'], '%Y-%m').month)\
                     - (start_month.year * 12 + start_month.month)
            if offset < 0:
                break
            for col in data.keys():
                data[col]['series'][offset] = item[col]

        output = {'categories': categories,
                  'series': [],
                  }

        for col in sorted(data.keys()):
            output['series'].append({'data': data[col]['series'], 'name': data[col]['label']})

        return output

    def get_total_plays_by_top_10_platforms(self, time_range='30', x_axis='media', y_axis='plays', server_id=None, user_id=None, grouping=None):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'

        if server_id and server_id.isdigit():
            server_cond = 'AND session_history.server_id = %s ' % server_id
            server_cond2 = 'WHERE id = %s ' % server_id
        elif session.get_session_shared_servers():
            allowed_servers = ','.join(session.get_session_shared_servers())
            server_cond = 'AND session_history.server_id IN (%s) ' % allowed_servers
            server_cond2 = 'WHERE id IN (%s) ' % allowed_servers
        else:
            server_cond = ''
            server_cond2 = ''

        user_cond = ''
        if session.get_session_user_id() and user_id and user_id != str(session.get_session_user_id()):
            user_cond = 'AND session_history.user_id = %s ' % session.get_session_user_id()
        elif user_id and user_id.isdigit():
            user_cond = 'AND session_history.user_id = %s ' % user_id

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        group_by = 'reference_id' if grouping else 'id'

        try:
            if x_axis == 'media' and y_axis == 'plays':
                data = {'tv_count': {'label': 'TV', 'series': []},
                        'movie_count': {'label': 'Movies', 'series': []},
                        'music_count': {'label': 'Music', 'series': []},
                        }
                query = 'SELECT platform, ' \
                        'SUM(CASE WHEN media_type = "episode" THEN 1 ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "movie" THEN 1 ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "track" THEN 1 ELSE 0 END) AS music_count, ' \
                        'COUNT(id) AS total_count ' \
                        'FROM (SELECT * FROM session_history GROUP BY %s) AS session_history ' \
                        'WHERE (datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime")) %s %s' \
                        'GROUP BY platform ' \
                        'ORDER BY total_count DESC ' \
                        'LIMIT 10' % (group_by, time_range, server_cond, user_cond)

                result = monitor_db.select(query)

            elif x_axis == 'media' and y_axis == 'duration':
                data = {'tv_count': {'label': 'TV', 'series': []},
                        'movie_count': {'label': 'Movies', 'series': []},
                        'music_count': {'label': 'Music', 'series': []},
                        }
                query = 'SELECT platform, ' \
                        'SUM(CASE WHEN media_type = "episode" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "movie" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "track" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS music_count, ' \
                        'SUM(CASE WHEN stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS total_duration ' \
                        'FROM session_history ' \
                        'WHERE (datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime")) %s %s' \
                        'GROUP BY platform ' \
                        'ORDER BY total_duration DESC ' \
                        'LIMIT 10' % (time_range, server_cond, user_cond)

                result = monitor_db.select(query)

            elif x_axis == 'server' and y_axis == 'plays':
                query = 'SELECT id, pms_name FROM servers %s ORDER BY pms_name' % server_cond2
                servers = monitor_db.select(query)
                columns = ''
                data = {}
                cnt = 0
                for server in servers:
                    columns += 'SUM(CASE WHEN server_id = %s THEN 1 ELSE 0 END) AS %s, ' % (
                        server['id'], "'" + str(cnt) + "'")
                    data[str(cnt)] = {'label': server['pms_name'], 'series': []}
                    cnt += 1
                columns = columns.rstrip(', ')

                query = 'SELECT platform, ' \
                        'COUNT(id) AS total_count, ' \
                        '%s ' \
                        'FROM (SELECT * FROM session_history GROUP BY %s) AS session_history ' \
                        'WHERE (datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime")) %s %s' \
                        'GROUP BY platform ' \
                        'ORDER BY total_count DESC ' \
                        'LIMIT 10' % (columns, group_by, time_range, server_cond, user_cond)

                result = monitor_db.select(query)

            elif x_axis == 'server' and y_axis == 'duration':
                query = 'SELECT id, pms_name FROM servers %s ORDER BY pms_name' % server_cond2
                servers = monitor_db.select(query)
                columns = ''
                data = {}
                cnt = 0
                for server in servers:
                    columns += 'SUM(CASE WHEN server_id = %s AND stopped > 0 THEN (stopped - started) ' \
                               '- (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS %s, ' \
                               % (server['id'], "'" + str(cnt) + "'")
                    data[str(cnt)] = {'label': server['pms_name'], 'series': []}
                    cnt += 1
                columns = columns.rstrip(', ')

                query = 'SELECT platform, ' \
                        'SUM(CASE WHEN stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS total_duration, ' \
                        '%s ' \
                        'FROM session_history ' \
                        'WHERE (datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime")) %s %s' \
                        'GROUP BY platform ' \
                        'ORDER BY total_duration DESC ' \
                        'LIMIT 10' % (columns, time_range, server_cond, user_cond)

                result = monitor_db.select(query)

        except Exception as e:
            logger.warn(u"Tautulli Graphs :: Unable to execute database query for get_total_plays_by_top_10_platforms: %s." % e)
            return None

        for col in data.keys():
            data[col]['series'] = [0 for x in range(len(result))]

        categories = []
        offset = 0
        for item in result:
            categories.append(common.PLATFORM_NAME_OVERRIDES.get(item['platform'], item['platform']))
            for col in data.keys():
                data[col]['series'][offset] = item[col]
            offset += 1

        output = {'categories': categories,
                  'series': [],
                  }

        for col in sorted(data.keys()):
            output['series'].append({'data': data[col]['series'], 'name': data[col]['label']})

        return output

    def get_total_plays_by_top_10_users(self, time_range='30', x_axis='media', y_axis='plays', server_id=None, user_id=None, grouping=None):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'

        if server_id and server_id.isdigit():
            server_cond = 'AND session_history.server_id = %s ' % server_id
            server_cond2 = 'WHERE id = %s ' % server_id
        elif session.get_session_shared_servers():
            allowed_servers = ','.join(session.get_session_shared_servers())
            server_cond = 'AND session_history.server_id IN (%s) ' % allowed_servers
            server_cond2 = 'WHERE id IN (%s) ' % allowed_servers
        else:
            server_cond = ''
            server_cond2 = ''

        user_cond = ''
        if session.get_session_user_id() and user_id and user_id != str(session.get_session_user_id()):
            user_cond = 'AND session_history.user_id = %s ' % session.get_session_user_id()
        elif user_id and user_id.isdigit():
            user_cond = 'AND session_history.user_id = %s ' % user_id

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        group_by = 'reference_id' if grouping else 'id'

        try:
            if x_axis == 'media' and y_axis == 'plays':
                data = {'tv_count': {'label': 'TV', 'series': []},
                        'movie_count': {'label': 'Movies', 'series': []},
                        'music_count': {'label': 'Music', 'series': []},
                        }
                query = 'SELECT ' \
                        'users.user_id, users.username, ' \
                        '(CASE WHEN users.friendly_name IS NULL OR TRIM(users.friendly_name) = "" ' \
                        ' THEN users.username ELSE users.friendly_name END) AS friendly_name,' \
                        'SUM(CASE WHEN media_type = "episode" THEN 1 ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "movie" THEN 1 ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "track" THEN 1 ELSE 0 END) AS music_count, ' \
                        'COUNT(session_history.id) AS total_count ' \
                        'FROM (SELECT * FROM session_history GROUP BY %s) AS session_history ' \
                        'JOIN users ON session_history.user_id = users.user_id ' \
                        'WHERE (datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime")) %s %s' \
                        'GROUP BY session_history.user_id ' \
                        'ORDER BY total_count DESC ' \
                        'LIMIT 10' % (group_by, time_range, server_cond, user_cond)

                result = monitor_db.select(query)

            elif x_axis == 'media' and y_axis == 'duration':
                data = {'tv_count': {'label': 'TV', 'series': []},
                        'movie_count': {'label': 'Movies', 'series': []},
                        'music_count': {'label': 'Music', 'series': []},
                        }
                query = 'SELECT ' \
                        'users.user_id, users.username, ' \
                        '(CASE WHEN users.friendly_name IS NULL OR TRIM(users.friendly_name) = "" ' \
                        ' THEN users.username ELSE users.friendly_name END) AS friendly_name,' \
                        'SUM(CASE WHEN media_type = "episode" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "movie" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "track" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS music_count, ' \
                        'SUM(CASE WHEN stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS total_duration ' \
                        'FROM session_history ' \
                        'JOIN users ON session_history.user_id = users.user_id ' \
                        'WHERE (datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime")) %s %s' \
                        'GROUP BY session_history.user_id ' \
                        'ORDER BY total_duration DESC ' \
                        'LIMIT 10' % (time_range, server_cond, user_cond)

                result = monitor_db.select(query)

            elif x_axis == 'server' and y_axis == 'plays':
                query = 'SELECT id, pms_name FROM servers %s ORDER BY pms_name' % server_cond2
                servers = monitor_db.select(query)
                columns = ''
                data = {}
                cnt = 0
                for server in servers:
                    columns += 'SUM(CASE WHEN server_id = %s THEN 1 ELSE 0 END) AS %s, ' % (
                        server['id'], "'" + str(cnt) + "'")
                    data[str(cnt)] = {'label': server['pms_name'], 'series': []}
                    cnt += 1
                columns = columns.rstrip(', ')

                query = 'SELECT ' \
                        'users.user_id, users.username, ' \
                        '(CASE WHEN users.friendly_name IS NULL OR TRIM(users.friendly_name) = "" ' \
                        ' THEN users.username ELSE users.friendly_name END) AS friendly_name,' \
                        'COUNT(session_history.id) AS total_count, ' \
                        '%s ' \
                        'FROM (SELECT * FROM session_history GROUP BY %s) AS session_history ' \
                        'JOIN users ON session_history.user_id = users.user_id ' \
                        'WHERE (datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime")) %s %s' \
                        'GROUP BY session_history.user_id ' \
                        'ORDER BY total_count DESC ' \
                        'LIMIT 10' % (columns, group_by, time_range, server_cond, user_cond)

                result = monitor_db.select(query)

            elif x_axis == 'server' and y_axis == 'duration':
                query = 'SELECT id, pms_name FROM servers %s ORDER BY pms_name' % server_cond2
                servers = monitor_db.select(query)
                columns = ''
                data = {}
                cnt = 0
                for server in servers:
                    columns += 'SUM(CASE WHEN server_id = %s AND stopped > 0 THEN (stopped - started) ' \
                               '- (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS %s, ' \
                               % (server['id'], "'" + str(cnt) + "'")
                    data[str(cnt)] = {'label': server['pms_name'], 'series': []}
                    cnt += 1
                columns = columns.rstrip(', ')

                query = 'SELECT ' \
                        'users.user_id, users.username, ' \
                        '(CASE WHEN users.friendly_name IS NULL OR TRIM(users.friendly_name) = "" ' \
                        ' THEN users.username ELSE users.friendly_name END) AS friendly_name,' \
                        'SUM(CASE WHEN stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS total_duration, ' \
                         '%s ' \
                       'FROM session_history ' \
                        'JOIN users ON session_history.user_id = users.user_id ' \
                        'WHERE (datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime")) %s %s' \
                        'GROUP BY session_history.user_id ' \
                        'ORDER BY total_duration DESC ' \
                        'LIMIT 10' % (columns, time_range, server_cond, user_cond)

                result = monitor_db.select(query)

        except Exception as e:
            logger.warn(u"Tautulli Graphs :: Unable to execute database query for get_total_plays_by_top_10_users: %s." % e)
            return None

        for col in data.keys():
            data[col]['series'] = [0 for x in range(len(result))]

        session_user_id = session.get_session_user_id()

        categories = []
        offset = 0
        for item in result:
            if session_user_id:
                categories.append(item['username'] if str(item['user_id']) == session_user_id else 'Plex User')
            else:
                categories.append(item['friendly_name'])
            for col in data.keys():
                data[col]['series'][offset] = item[col]
            offset += 1

        output = {'categories': categories,
                  'series': [],
                  }

        for col in sorted(data.keys()):
            output['series'].append({'data': data[col]['series'], 'name': data[col]['label']})

        return output

    def get_total_plays_per_stream_type(self, time_range='30', x_axis='media', y_axis='plays', server_id=None, user_id=None, grouping=None):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'

        if server_id and server_id.isdigit():
            server_cond = 'AND session_history.server_id = %s ' % server_id
        elif session.get_session_shared_servers():
            allowed_servers = ','.join(session.get_session_shared_servers())
            server_cond = 'AND session_history.server_id IN (%s) ' % allowed_servers
        else:
            server_cond = ''

        user_cond = ''
        if session.get_session_user_id() and user_id and user_id != str(session.get_session_user_id()):
            user_cond = 'AND session_history.user_id = %s ' % session.get_session_user_id()
        elif user_id and user_id.isdigit():
            user_cond = 'AND session_history.user_id = %s ' % user_id

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        group_by = 'reference_id' if grouping else 'id'

        try:
            if y_axis == 'plays':
                query = 'SELECT date(session_history.started, "unixepoch", "localtime") AS date_played, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "direct play" ' \
                        'THEN 1 ELSE 0 END) AS dp_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "copy" ' \
                        'THEN 1 ELSE 0 END) AS ds_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "transcode" ' \
                        'THEN 1 ELSE 0 END) AS tc_count ' \
                        'FROM (SELECT * FROM session_history ' \
                        'GROUP BY date(session_history.started, "unixepoch", "localtime"), %s) ' \
                        'AS session_history ' \
                        'JOIN session_history_media_info ON session_history.id = session_history_media_info.id ' \
                        'WHERE (datetime(started, "unixepoch", "localtime") >= ' \
                        'datetime("now", "-%s days", "localtime")) AND ' \
                        '(session_history.media_type = "episode" OR ' \
                        'session_history.media_type = "movie" OR ' \
                        'session_history.media_type = "track") %s %s' \
                        'GROUP BY date_played ' \
                        'ORDER BY started ASC' % (group_by, time_range, server_cond, user_cond)

                result = monitor_db.select(query)
            elif y_axis == 'duration':
                query = 'SELECT date(session_history.started, "unixepoch", "localtime") AS date_played, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "direct play" ' \
                        'AND session_history.stopped > 0 THEN (session_history.stopped - session_history.started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS dp_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "copy" ' \
                        'AND session_history.stopped > 0 THEN (session_history.stopped - session_history.started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS ds_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "transcode" ' \
                        'AND session_history.stopped > 0 THEN (session_history.stopped - session_history.started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS tc_count ' \
                        'FROM session_history ' \
                        'JOIN session_history_media_info ON session_history.id = session_history_media_info.id ' \
                        'WHERE datetime(started, "unixepoch", "localtime") >= ' \
                        'datetime("now", "-%s days", "localtime") AND ' \
                        '(session_history.media_type = "episode" OR session_history.media_type = "movie" OR ' \
                        'session_history.media_type = "track") %s %s' \
                        'GROUP BY date_played ' \
                        'ORDER BY started ASC' % (time_range, server_cond, user_cond)

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn(u"Tautulli Graphs :: Unable to execute database query for get_total_plays_per_stream_type: %s." % e)
            return None

        # create our date range as some days may not have any data
        # but we still want to display them
        base = datetime.date.today()
        date_list = [base - datetime.timedelta(days=x) for x in range(0, int(time_range))]

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []

        for date_item in sorted(date_list):
            date_string = date_item.strftime('%Y-%m-%d')
            categories.append(date_string)
            series_1_value = 0
            series_2_value = 0
            series_3_value = 0
            for item in result:
                if date_string == item['date_played']:
                    series_1_value = item['dp_count']
                    series_2_value = item['ds_count']
                    series_3_value = item['tc_count']
                    break
                else:
                    series_1_value = 0
                    series_2_value = 0
                    series_3_value = 0

            series_1.append(series_1_value)
            series_2.append(series_2_value)
            series_3.append(series_3_value)

        series_1_output = {'name': 'Direct Play',
                           'data': series_1}
        series_2_output = {'name': 'Direct Stream',
                           'data': series_2}
        series_3_output = {'name': 'Transcode',
                           'data': series_3}

        output = {'categories': categories,
                  'series': [series_1_output, series_2_output, series_3_output]}
        return output

    def get_total_plays_by_source_resolution(self, time_range='30', x_axis='media', y_axis='plays', server_id=None, user_id=None, grouping=None):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'

        if server_id and server_id.isdigit():
            server_cond = 'AND session_history.server_id = %s ' % server_id
        elif session.get_session_shared_servers():
            allowed_servers = ','.join(session.get_session_shared_servers())
            server_cond = 'AND session_history.server_id IN (%s) ' % allowed_servers
        else:
            server_cond = ''

        user_cond = ''
        if session.get_session_user_id() and user_id and user_id != str(session.get_session_user_id()):
            user_cond = 'AND session_history.user_id = %s ' % session.get_session_user_id()
        elif user_id and user_id.isdigit():
            user_cond = 'AND session_history.user_id = %s ' % user_id

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        group_by = 'reference_id' if grouping else 'id'

        try:
            if y_axis == 'plays':
                query = 'SELECT UPPER(session_history_media_info.video_resolution) AS resolution, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "direct play" ' \
                        'THEN 1 ELSE 0 END) AS dp_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "copy" ' \
                        'THEN 1 ELSE 0 END) AS ds_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "transcode" ' \
                        'THEN 1 ELSE 0 END) AS tc_count, ' \
                        'COUNT(session_history.id) AS total_count ' \
                        'FROM (SELECT * FROM session_history GROUP BY %s) AS session_history ' \
                        'JOIN session_history_media_info ON session_history.id = session_history_media_info.id ' \
                        'WHERE (datetime(started, "unixepoch", "localtime") >= ' \
                        'datetime("now", "-%s days", "localtime")) AND ' \
                        '(session_history.media_type = "episode" OR session_history.media_type = "movie") %s %s' \
                        'GROUP BY resolution ' \
                        'ORDER BY total_count DESC ' \
                        'LIMIT 10' % (group_by, time_range, server_cond, user_cond)

                result = monitor_db.select(query)
            else:
                query = 'SELECT UPPER(session_history_media_info.video_resolution) AS resolution,' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "direct play" ' \
                        'AND session_history.stopped > 0 THEN (session_history.stopped - session_history.started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS dp_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "copy" ' \
                        'AND session_history.stopped > 0 THEN (session_history.stopped - session_history.started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS ds_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "transcode" ' \
                        'AND session_history.stopped > 0 THEN (session_history.stopped - session_history.started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS tc_count, ' \
                        'SUM(CASE WHEN stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS total_duration ' \
                        'FROM session_history ' \
                        'JOIN session_history_media_info ON session_history.id = session_history_media_info.id ' \
                        'WHERE (datetime(started, "unixepoch", "localtime") >= ' \
                        'datetime("now", "-%s days", "localtime")) AND ' \
                        '(session_history.media_type = "episode" OR session_history.media_type = "movie") %s %s' \
                        'GROUP BY resolution ' \
                        'ORDER BY total_duration DESC ' \
                        'LIMIT 10' % (time_range, server_cond, user_cond)

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn(u"Tautulli Graphs :: Unable to execute database query for get_total_plays_by_source_resolution: %s." % e)
            return None

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []

        for item in result:
            if item['resolution'] not in ('4k', 'unknown'):
                item['resolution'] = item['resolution'].upper()
            if item['resolution'].isdigit():
                item['resolution'] += 'p'
            categories.append(item['resolution'])
            series_1.append(item['dp_count'])
            series_2.append(item['ds_count'])
            series_3.append(item['tc_count'])

        series_1_output = {'name': 'Direct Play',
                           'data': series_1}
        series_2_output = {'name': 'Direct Stream',
                           'data': series_2}
        series_3_output = {'name': 'Transcode',
                           'data': series_3}

        output = {'categories': categories,
                  'series': [series_1_output, series_2_output, series_3_output]}
        return output

    def get_total_plays_by_stream_resolution(self, time_range='30', x_axis='media', y_axis='plays', server_id=None, user_id=None, grouping=None):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'

        if server_id and server_id.isdigit():
            server_cond = 'AND session_history.server_id = %s ' % server_id
        elif session.get_session_shared_servers():
            allowed_servers = ','.join(session.get_session_shared_servers())
            server_cond = 'AND session_history.server_id IN (%s) ' % allowed_servers
        else:
            server_cond = ''

        user_cond = ''
        if session.get_session_user_id() and user_id and user_id != str(session.get_session_user_id()):
            user_cond = 'AND session_history.user_id = %s ' % session.get_session_user_id()
        elif user_id and user_id.isdigit():
            user_cond = 'AND session_history.user_id = %s ' % user_id

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        group_by = 'reference_id' if grouping else 'id'

        try:
            if y_axis == 'plays':
                query = 'SELECT ' \
                        '(CASE WHEN session_history_media_info.stream_video_resolution IS NULL THEN ' \
                        '(CASE WHEN session_history_media_info.video_decision = "transcode" THEN ' \
                        '(CASE ' \
                        'WHEN session_history_media_info.transcode_height <= 360 THEN "SD" ' \
                        'WHEN session_history_media_info.transcode_height <= 480 THEN "480" ' \
                        'WHEN session_history_media_info.transcode_height <= 576 THEN "576" ' \
                        'WHEN session_history_media_info.transcode_height <= 720 THEN "720" ' \
                        'WHEN session_history_media_info.transcode_height <= 1080 THEN "1080" ' \
                        'WHEN session_history_media_info.transcode_height <= 1440 THEN "QHD" ' \
                        'WHEN session_history_media_info.transcode_height <= 2160 THEN "4k" ' \
                        'ELSE "unknown" END) ELSE UPPER(session_history_media_info.video_resolution) END) ' \
                        'ELSE UPPER(session_history_media_info.stream_video_resolution) END) AS resolution, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "direct play" ' \
                        'THEN 1 ELSE 0 END) AS dp_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "copy" ' \
                        'THEN 1 ELSE 0 END) AS ds_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "transcode" '\
                        'THEN 1 ELSE 0 END) AS tc_count, ' \
                        'COUNT(session_history.id) AS total_count ' \
                        'FROM (SELECT * FROM session_history GROUP BY %s) AS session_history ' \
                        'JOIN session_history_media_info ON session_history.id = session_history_media_info.id ' \
                        'WHERE (datetime(started, "unixepoch", "localtime") >= ' \
                        'datetime("now", "-%s days", "localtime")) AND ' \
                        '(session_history.media_type = "episode" OR session_history.media_type = "movie") %s %s' \
                        'GROUP BY resolution ' \
                        'ORDER BY total_count DESC ' \
                        'LIMIT 10' % (group_by, time_range, server_cond, user_cond)

                result = monitor_db.select(query)
            else:
                query = 'SELECT ' \
                        '(CASE WHEN session_history_media_info.stream_video_resolution IS NULL THEN ' \
                        '(CASE WHEN session_history_media_info.video_decision = "transcode" THEN ' \
                        '(CASE ' \
                        'WHEN session_history_media_info.transcode_height <= 360 THEN "SD" ' \
                        'WHEN session_history_media_info.transcode_height <= 480 THEN "480" ' \
                        'WHEN session_history_media_info.transcode_height <= 576 THEN "576" ' \
                        'WHEN session_history_media_info.transcode_height <= 720 THEN "720" ' \
                        'WHEN session_history_media_info.transcode_height <= 1080 THEN "1080" ' \
                        'WHEN session_history_media_info.transcode_height <= 1440 THEN "QHD" ' \
                        'WHEN session_history_media_info.transcode_height <= 2160 THEN "4k" ' \
                        'ELSE "unknown" END) ELSE UPPER(session_history_media_info.video_resolution) END) ' \
                        'ELSE UPPER(session_history_media_info.stream_video_resolution) END) AS resolution, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "direct play" ' \
                        'AND session_history.stopped > 0 THEN (session_history.stopped - session_history.started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS dp_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "copy" ' \
                        'AND session_history.stopped > 0 THEN (session_history.stopped - session_history.started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS ds_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "transcode" ' \
                        'AND session_history.stopped > 0 THEN (session_history.stopped - session_history.started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS tc_count, ' \
                        'SUM(CASE WHEN stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS total_duration ' \
                        'FROM session_history ' \
                        'JOIN session_history_media_info ON session_history.id = session_history_media_info.id ' \
                        'WHERE (datetime(started, "unixepoch", "localtime") >= ' \
                        'datetime("now", "-%s days", "localtime")) AND ' \
                        '(session_history.media_type = "episode" OR session_history.media_type = "movie") %s %s' \
                        'GROUP BY resolution ' \
                        'ORDER BY total_duration DESC ' \
                        'LIMIT 10' % (time_range, server_cond, user_cond)

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn(u"Tautulli Graphs :: Unable to execute database query for get_total_plays_by_stream_resolution: %s." % e)
            return None

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []

        for item in result:
            if item['resolution'] not in ('4k', 'unknown'):
                item['resolution'] = item['resolution'].upper()
            if item['resolution'].isdigit():
                item['resolution'] += 'p'
            categories.append(item['resolution'])
            series_1.append(item['dp_count'])
            series_2.append(item['ds_count'])
            series_3.append(item['tc_count'])

        series_1_output = {'name': 'Direct Play',
                           'data': series_1}
        series_2_output = {'name': 'Direct Stream',
                           'data': series_2}
        series_3_output = {'name': 'Transcode',
                           'data': series_3}

        output = {'categories': categories,
                  'series': [series_1_output, series_2_output, series_3_output]}
        return output

    def get_stream_type_by_top_10_platforms(self, time_range='30', x_axis='media', y_axis='plays', server_id=None, user_id=None, grouping=None):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'

        if server_id and server_id.isdigit():
            server_cond = 'AND session_history.server_id = %s ' % server_id
        elif session.get_session_shared_servers():
            allowed_servers = ','.join(session.get_session_shared_servers())
            server_cond = 'AND session_history.server_id IN (%s) ' % allowed_servers
        else:
            server_cond = ''

        user_cond = ''
        if session.get_session_user_id() and user_id and user_id != str(session.get_session_user_id()):
            user_cond = 'AND session_history.user_id = %s ' % session.get_session_user_id()
        elif user_id and user_id.isdigit():
            user_cond = 'AND session_history.user_id = %s ' % user_id

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        group_by = 'reference_id' if grouping else 'id'

        try:
            if y_axis == 'plays':
                query = 'SELECT session_history.platform AS platform, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "direct play" ' \
                        'THEN 1 ELSE 0 END) AS dp_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "copy" ' \
                        'THEN 1 ELSE 0 END) AS ds_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "transcode" ' \
                        'THEN 1 ELSE 0 END) AS tc_count, ' \
                        'COUNT(session_history.id) AS total_count ' \
                        'FROM (SELECT * FROM session_history GROUP BY %s) AS session_history ' \
                        'JOIN session_history_media_info ON session_history.id = session_history_media_info.id ' \
                        'WHERE datetime(started, "unixepoch", "localtime") >= ' \
                        'datetime("now", "-%s days", "localtime") AND ' \
                        '(session_history.media_type = "episode" OR ' \
                        'session_history.media_type = "movie" OR ' \
                        'session_history.media_type = "track") %s %s' \
                        'GROUP BY platform ' \
                        'ORDER BY total_count DESC LIMIT 10' % (group_by, time_range, server_cond, user_cond)

                result = monitor_db.select(query)
            else:
                query = 'SELECT session_history.platform AS platform, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "direct play" ' \
                        'AND session_history.stopped > 0 THEN (session_history.stopped - session_history.started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS dp_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "copy" ' \
                        'AND session_history.stopped > 0 THEN (session_history.stopped - session_history.started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS ds_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "transcode" ' \
                        'AND session_history.stopped > 0 THEN (session_history.stopped - session_history.started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS tc_count, ' \
                        'SUM(CASE WHEN session_history.stopped > 0 ' \
                        'THEN (session_history.stopped - session_history.started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS total_duration ' \
                        'FROM session_history ' \
                        'JOIN session_history_media_info ON session_history.id = session_history_media_info.id ' \
                        'WHERE datetime(started, "unixepoch", "localtime") >= ' \
                        'datetime("now", "-%s days", "localtime") AND ' \
                        '(session_history.media_type = "episode" OR ' \
                        'session_history.media_type = "movie" OR ' \
                        'session_history.media_type = "track") %s %s' \
                        'GROUP BY platform ' \
                        'ORDER BY total_duration DESC LIMIT 10' % (time_range, server_cond, user_cond)

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn(u"Tautulli Graphs :: Unable to execute database query for get_stream_type_by_top_10_platforms: %s." % e)
            return None

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []

        for item in result:
            categories.append(common.PLATFORM_NAME_OVERRIDES.get(item['platform'], item['platform']))
            series_1.append(item['dp_count'])
            series_2.append(item['ds_count'])
            series_3.append(item['tc_count'])

        series_1_output = {'name': 'Direct Play',
                           'data': series_1}
        series_2_output = {'name': 'Direct Stream',
                           'data': series_2}
        series_3_output = {'name': 'Transcode',
                           'data': series_3}

        output = {'categories': categories,
                  'series': [series_1_output, series_2_output, series_3_output]}

        return output

    def get_stream_type_by_top_10_users(self, time_range='30', x_axis='media', y_axis='plays', server_id=None, user_id=None, grouping=None):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'

        if server_id and server_id.isdigit():
            server_cond = 'AND session_history.server_id = %s ' % server_id
        elif session.get_session_shared_servers():
            allowed_servers = ','.join(session.get_session_shared_servers())
            server_cond = 'AND session_history.server_id IN (%s) ' % allowed_servers
        else:
            server_cond = ''

        user_cond = ''
        if session.get_session_user_id() and user_id and user_id != str(session.get_session_user_id()):
            user_cond = 'AND session_history.user_id = %s ' % session.get_session_user_id()
        elif user_id and user_id.isdigit():
            user_cond = 'AND session_history.user_id = %s ' % user_id

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        group_by = 'reference_id' if grouping else 'id'

        try:
            if y_axis == 'plays':
                query = 'SELECT ' \
                        'users.user_id, users.username, ' \
                        '(CASE WHEN users.friendly_name IS NULL OR TRIM(users.friendly_name) = "" ' \
                        ' THEN users.username ELSE users.friendly_name END) AS friendly_name,' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "direct play" ' \
                        'THEN 1 ELSE 0 END) AS dp_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "copy" ' \
                        'THEN 1 ELSE 0 END) AS ds_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "transcode" ' \
                        'THEN 1 ELSE 0 END) AS tc_count, ' \
                        'COUNT(session_history.id) AS total_count ' \
                        'FROM (SELECT * FROM session_history GROUP BY %s) AS session_history ' \
                        'JOIN users ON session_history.user_id = users.user_id ' \
                        'JOIN session_history_media_info ON session_history.id = session_history_media_info.id ' \
                        'WHERE datetime(started, "unixepoch", "localtime") >= ' \
                        'datetime("now", "-%s days", "localtime") AND ' \
                        '(session_history.media_type = "episode" OR ' \
                        'session_history.media_type = "movie" OR ' \
                        'session_history.media_type = "track") %s %s' \
                        'GROUP BY username ' \
                        'ORDER BY total_count DESC LIMIT 10' % (group_by, time_range, server_cond, user_cond)

                result = monitor_db.select(query)
            else:
                query = 'SELECT ' \
                        'users.user_id, users.username, ' \
                        '(CASE WHEN users.friendly_name IS NULL OR TRIM(users.friendly_name) = "" ' \
                        ' THEN users.username ELSE users.friendly_name END) AS friendly_name,' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "direct play" ' \
                        'AND session_history.stopped > 0 THEN (session_history.stopped - session_history.started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS dp_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "copy" ' \
                        'AND session_history.stopped > 0 THEN (session_history.stopped - session_history.started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS ds_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "transcode" ' \
                        'AND session_history.stopped > 0 THEN (session_history.stopped - session_history.started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS tc_count, ' \
                        'SUM(CASE WHEN session_history.stopped > 0 ' \
                        'THEN (session_history.stopped - session_history.started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS total_duration ' \
                        'FROM session_history ' \
                        'JOIN users ON session_history.user_id = users.user_id ' \
                        'JOIN session_history_media_info ON session_history.id = session_history_media_info.id ' \
                        'WHERE datetime(started, "unixepoch", "localtime") >= ' \
                        'datetime("now", "-%s days", "localtime") AND ' \
                        '(session_history.media_type = "episode" OR ' \
                        'session_history.media_type = "movie" OR ' \
                        'session_history.media_type = "track") %s %s' \
                        'GROUP BY username ' \
                        'ORDER BY total_duration DESC LIMIT 10' % (time_range, server_cond, user_cond)

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn(u"Tautulli Graphs :: Unable to execute database query for get_stream_type_by_top_10_users: %s." % e)
            return None

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []

        session_user_id = session.get_session_user_id()

        for item in result:
            if session_user_id:
                categories.append(item['username'] if str(item['user_id']) == session_user_id else 'Plex User')
            else:
                categories.append(item['friendly_name'])
            series_1.append(item['dp_count'])
            series_2.append(item['ds_count'])
            series_3.append(item['tc_count'])

        series_1_output = {'name': 'Direct Play',
                           'data': series_1}
        series_2_output = {'name': 'Direct Stream',
                           'data': series_2}
        series_3_output = {'name': 'Transcode',
                           'data': series_3}

        output = {'categories': categories,
                  'series': [series_1_output, series_2_output, series_3_output]}

        return output
