# -*- coding: utf-8 -*-

# This file is part of Tautulli.
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

from __future__ import unicode_literals
from future.builtins import str
from future.builtins import range
from future.builtins import object

import arrow
import datetime

import plexpy
if plexpy.PYTHON2:
    import common
    import database
    import helpers
    import logger
    import libraries
    import session
else:
    from plexpy import common
    from plexpy import database
    from plexpy import helpers
    from plexpy import logger
    from plexpy import libraries
    from plexpy import session


class Graphs(object):

    def __init__(self):
        pass

    def get_total_plays_per_day(self, time_range='30', y_axis='plays', user_id=None, grouping=None):
        monitor_db = database.MonitorDatabase()

        time_range = helpers.cast_to_int(time_range) or 30
        timestamp = helpers.timestamp() - time_range * 24 * 60 * 60

        user_cond = ''
        if session.get_session_user_id() and user_id and user_id != str(session.get_session_user_id()):
            user_cond = 'AND session_history.user_id = %s ' % session.get_session_user_id()
        elif user_id and user_id.isdigit():
            user_cond = 'AND session_history.user_id = %s ' % user_id

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        group_by = 'session_history.reference_id' if grouping else 'session_history.id'

        try:
            if y_axis == 'plays':
                query = 'SELECT sh.date_played, ' \
                        'SUM(CASE WHEN sh.media_type = "episode" AND shm.live = 0 THEN 1 ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN sh.media_type = "movie" AND shm.live = 0 THEN 1 ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN sh.media_type = "track" AND shm.live = 0 THEN 1 ELSE 0 END) AS music_count, ' \
                        'SUM(shm.live) AS live_count ' \
                        'FROM (SELECT *,' \
                        '      date(started, "unixepoch", "localtime") AS date_played ' \
                        '    FROM session_history ' \
                        '    WHERE session_history.stopped >= %s %s ' \
                        '    GROUP BY date_played, %s) AS sh ' \
                        'JOIN session_history_metadata AS shm ON shm.id = sh.id ' \
                        'GROUP BY sh.date_played ' \
                        'ORDER BY sh.started' % (timestamp, user_cond, group_by)

                result = monitor_db.select(query)
            else:
                query = 'SELECT sh.date_played, ' \
                        'SUM(CASE WHEN sh.media_type = "episode" AND shm.live = 0 ' \
                        '  THEN sh.d ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN sh.media_type = "movie" AND shm.live = 0 ' \
                        '  THEN sh.d ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN sh.media_type = "track" AND shm.live = 0 ' \
                        '  THEN sh.d ELSE 0 END) AS music_count, ' \
                        'SUM(CASE WHEN shm.live = 1 ' \
                        '  THEN sh.d ELSE 0 END) AS live_count ' \
                        'FROM (SELECT *,' \
                        '      date(started, "unixepoch", "localtime") AS date_played,' \
                        '      SUM(CASE WHEN stopped > 0 THEN (stopped - started) - ' \
                        '        (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) ' \
                        '        AS d ' \
                        '    FROM session_history ' \
                        '    WHERE session_history.stopped >= %s %s' \
                        '    GROUP BY date_played, %s) AS sh ' \
                        'JOIN session_history_metadata AS shm ON shm.id = sh.id ' \
                        'GROUP BY sh.date_played ' \
                        'ORDER BY sh.started' % (timestamp, user_cond, group_by)

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn("Tautulli Graphs :: Unable to execute database query for get_total_plays_per_day: %s." % e)
            return None

        # create our date range as some days may not have any data
        # but we still want to display them
        base = datetime.date.today()
        date_list = [base - datetime.timedelta(days=x) for x in range(0, int(time_range))]

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []
        series_4 = []

        for date_item in sorted(date_list):
            date_string = date_item.strftime('%Y-%m-%d')
            categories.append(date_string)
            series_1_value = 0
            series_2_value = 0
            series_3_value = 0
            series_4_value = 0
            for item in result:
                if date_string == item['date_played']:
                    series_1_value = item['tv_count']
                    series_2_value = item['movie_count']
                    series_3_value = item['music_count']
                    series_4_value = item['live_count']
                    break
                else:
                    series_1_value = 0
                    series_2_value = 0
                    series_3_value = 0
                    series_4_value = 0

            series_1.append(series_1_value)
            series_2.append(series_2_value)
            series_3.append(series_3_value)
            series_4.append(series_4_value)

        series_1_output = {'name': 'TV',
                           'data': series_1}
        series_2_output = {'name': 'Movies',
                           'data': series_2}
        series_3_output = {'name': 'Music',
                           'data': series_3}
        series_4_output = {'name': 'Live TV',
                           'data': series_4}

        series_output = []
        if libraries.has_library_type('show'):
            series_output.append(series_1_output)
        if libraries.has_library_type('movie'):
            series_output.append(series_2_output)
        if libraries.has_library_type('artist'):
            series_output.append(series_3_output)
        if libraries.has_library_type('live'):
            series_output.append(series_4_output)

        output = {'categories': categories,
                  'series': series_output}
        return output

    def get_total_plays_per_dayofweek(self, time_range='30', y_axis='plays', user_id=None, grouping=None):
        monitor_db = database.MonitorDatabase()

        time_range = helpers.cast_to_int(time_range) or 30
        timestamp = helpers.timestamp() - time_range * 24 * 60 * 60

        user_cond = ''
        if session.get_session_user_id() and user_id and user_id != str(session.get_session_user_id()):
            user_cond = 'AND session_history.user_id = %s ' % session.get_session_user_id()
        elif user_id and user_id.isdigit():
            user_cond = 'AND session_history.user_id = %s ' % user_id

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        group_by = 'session_history.reference_id' if grouping else 'session_history.id'

        try:
            if y_axis == 'plays':
                query = 'SELECT sh.daynumber, ' \
                        '(CASE sh.daynumber ' \
                        '  WHEN 0 THEN "Sunday" ' \
                        '  WHEN 1 THEN "Monday" ' \
                        '  WHEN 2 THEN "Tuesday" ' \
                        '  WHEN 3 THEN "Wednesday" ' \
                        '  WHEN 4 THEN "Thursday" ' \
                        '  WHEN 5 THEN "Friday" ' \
                        '  ELSE "Saturday" END) AS dayofweek, ' \
                        'SUM(CASE WHEN sh.media_type = "episode" AND shm.live = 0 THEN 1 ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN sh.media_type = "movie" AND shm.live = 0 THEN 1 ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN sh.media_type = "track" AND shm.live = 0 THEN 1 ELSE 0 END) AS music_count, ' \
                        'SUM(shm.live) AS live_count ' \
                        'FROM (SELECT *, ' \
                        '      CAST(strftime("%%w", date(started, "unixepoch", "localtime")) AS INTEGER) AS daynumber' \
                        '    FROM session_history ' \
                        '    WHERE session_history.stopped >= %s %s ' \
                        '    GROUP BY daynumber, %s) AS sh ' \
                        'JOIN session_history_metadata AS shm ON shm.id = sh.id ' \
                        'GROUP BY dayofweek ' \
                        'ORDER BY sh.daynumber' % (timestamp, user_cond, group_by)

                result = monitor_db.select(query)
            else:
                query = 'SELECT sh.daynumber, ' \
                        '(CASE sh.daynumber ' \
                        '  WHEN 0 THEN "Sunday" ' \
                        '  WHEN 1 THEN "Monday" ' \
                        '  WHEN 2 THEN "Tuesday" ' \
                        '  WHEN 3 THEN "Wednesday" ' \
                        '  WHEN 4 THEN "Thursday" ' \
                        '  WHEN 5 THEN "Friday" ' \
                        '  ELSE "Saturday" END) AS dayofweek, ' \
                        'SUM(CASE WHEN sh.media_type = "episode" AND shm.live = 0 ' \
                        '  THEN sh.d ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN sh.media_type = "movie" AND shm.live = 0 ' \
                        '  THEN sh.d ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN sh.media_type = "track" AND shm.live = 0 ' \
                        '  THEN sh.d ELSE 0 END) AS music_count, ' \
                        'SUM(CASE WHEN shm.live = 1 ' \
                        '  THEN sh.d ELSE 0 END) AS live_count ' \
                        'FROM (SELECT *, ' \
                        '      CAST(strftime("%%w", date(started, "unixepoch", "localtime")) AS INTEGER) AS daynumber, ' \
                        '      SUM(CASE WHEN stopped > 0 THEN (stopped - started) - ' \
                        '        (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) ' \
                        '        AS d ' \
                        '    FROM session_history ' \
                        '    WHERE session_history.stopped >= %s %s' \
                        '    GROUP BY daynumber, %s) AS sh ' \
                        'JOIN session_history_metadata AS shm ON shm.id = sh.id ' \
                        'GROUP BY dayofweek ' \
                        'ORDER BY sh.daynumber' % (timestamp, user_cond, group_by)

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn("Tautulli Graphs :: Unable to execute database query for get_total_plays_per_dayofweek: %s." % e)
            return None

        if plexpy.CONFIG.WEEK_START_MONDAY:
            days_list = ['Monday', 'Tuesday', 'Wednesday',
                         'Thursday', 'Friday', 'Saturday', 'Sunday']
        else:
            days_list = ['Sunday', 'Monday', 'Tuesday', 'Wednesday',
                         'Thursday', 'Friday', 'Saturday']

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []
        series_4 = []

        for day_item in days_list:
            categories.append(day_item)
            series_1_value = 0
            series_2_value = 0
            series_3_value = 0
            series_4_value = 0
            for item in result:
                if day_item == item['dayofweek']:
                    series_1_value = item['tv_count']
                    series_2_value = item['movie_count']
                    series_3_value = item['music_count']
                    series_4_value = item['live_count']
                    break
                else:
                    series_1_value = 0
                    series_2_value = 0
                    series_3_value = 0
                    series_4_value = 0

            series_1.append(series_1_value)
            series_2.append(series_2_value)
            series_3.append(series_3_value)
            series_4.append(series_4_value)

        series_1_output = {'name': 'TV',
                           'data': series_1}
        series_2_output = {'name': 'Movies',
                           'data': series_2}
        series_3_output = {'name': 'Music',
                           'data': series_3}
        series_4_output = {'name': 'Live TV',
                           'data': series_4}

        series_output = []
        if libraries.has_library_type('show'):
            series_output.append(series_1_output)
        if libraries.has_library_type('movie'):
            series_output.append(series_2_output)
        if libraries.has_library_type('artist'):
            series_output.append(series_3_output)
        if libraries.has_library_type('live'):
            series_output.append(series_4_output)

        output = {'categories': categories,
                  'series': series_output}
        return output

    def get_total_plays_per_hourofday(self, time_range='30', y_axis='plays', user_id=None, grouping=None):
        monitor_db = database.MonitorDatabase()

        time_range = helpers.cast_to_int(time_range) or 30
        timestamp = helpers.timestamp() - time_range * 24 * 60 * 60

        user_cond = ''
        if session.get_session_user_id() and user_id and user_id != str(session.get_session_user_id()):
            user_cond = 'AND session_history.user_id = %s ' % session.get_session_user_id()
        elif user_id and user_id.isdigit():
            user_cond = 'AND session_history.user_id = %s ' % user_id

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        group_by = 'session_history.reference_id' if grouping else 'session_history.id'

        try:
            if y_axis == 'plays':
                query = 'SELECT sh.hourofday, ' \
                        'SUM(CASE WHEN sh.media_type = "episode" AND shm.live = 0 THEN 1 ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN sh.media_type = "movie" AND shm.live = 0 THEN 1 ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN sh.media_type = "track" AND shm.live = 0 THEN 1 ELSE 0 END) AS music_count, ' \
                        'SUM(shm.live) AS live_count ' \
                        'FROM (SELECT *, ' \
                        '      strftime("%%H", datetime(started, "unixepoch", "localtime")) AS hourofday' \
                        '    FROM session_history ' \
                        '    WHERE session_history.stopped >= %s %s ' \
                        '    GROUP BY hourofday, %s) AS sh ' \
                        'JOIN session_history_metadata AS shm ON shm.id = sh.id ' \
                        'GROUP BY sh.hourofday ' \
                        'ORDER BY sh.hourofday' % (timestamp, user_cond, group_by)

                result = monitor_db.select(query)
            else:
                query = 'SELECT sh.hourofday, ' \
                        'SUM(CASE WHEN sh.media_type = "episode" AND shm.live = 0 ' \
                        '  THEN sh.d ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN sh.media_type = "movie" AND shm.live = 0 ' \
                        '  THEN sh.d ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN sh.media_type = "track" AND shm.live = 0 ' \
                        '  THEN sh.d ELSE 0 END) AS music_count, ' \
                        'SUM(CASE WHEN shm.live = 1 ' \
                        '  THEN sh.d ELSE 0 END) AS live_count ' \
                        'FROM (SELECT *, ' \
                        '      strftime("%%H", datetime(started, "unixepoch", "localtime")) AS hourofday, ' \
                        '      SUM(CASE WHEN stopped > 0 THEN (stopped - started) - ' \
                        '        (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) ' \
                        '        AS d ' \
                        '    FROM session_history ' \
                        '    WHERE session_history.stopped >= %s %s' \
                        '    GROUP BY hourofday, %s) AS sh ' \
                        'JOIN session_history_metadata AS shm ON shm.id = sh.id ' \
                        'GROUP BY sh.hourofday ' \
                        'ORDER BY sh.hourofday' % (timestamp, user_cond, group_by)

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn("Tautulli Graphs :: Unable to execute database query for get_total_plays_per_hourofday: %s." % e)
            return None

        hours_list = ['00', '01', '02', '03', '04', '05',
                      '06', '07', '08', '09', '10', '11',
                      '12', '13', '14', '15', '16', '17',
                      '18', '19', '20', '21', '22', '23']

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []
        series_4 = []

        for hour_item in hours_list:
            categories.append(hour_item)
            series_1_value = 0
            series_2_value = 0
            series_3_value = 0
            series_4_value = 0
            for item in result:
                if hour_item == item['hourofday']:
                    series_1_value = item['tv_count']
                    series_2_value = item['movie_count']
                    series_3_value = item['music_count']
                    series_4_value = item['live_count']
                    break
                else:
                    series_1_value = 0
                    series_2_value = 0
                    series_3_value = 0
                    series_4_value = 0

            series_1.append(series_1_value)
            series_2.append(series_2_value)
            series_3.append(series_3_value)
            series_4.append(series_4_value)

        series_1_output = {'name': 'TV',
                           'data': series_1}
        series_2_output = {'name': 'Movies',
                           'data': series_2}
        series_3_output = {'name': 'Music',
                           'data': series_3}
        series_4_output = {'name': 'Live TV',
                           'data': series_4}

        series_output = []
        if libraries.has_library_type('show'):
            series_output.append(series_1_output)
        if libraries.has_library_type('movie'):
            series_output.append(series_2_output)
        if libraries.has_library_type('artist'):
            series_output.append(series_3_output)
        if libraries.has_library_type('live'):
            series_output.append(series_4_output)

        output = {'categories': categories,
                  'series': series_output}
        return output

    def get_total_additions_per_day(self, time_range='30', growth=False):
        monitor_db = database.MonitorDatabase()

        time_range = helpers.cast_to_int(time_range) or 30
        timestamp = helpers.timestamp() - time_range * 24 * 60 * 60

        join_statement = ' AS lsi JOIN library_sections AS ls ON ' \
	                     'lsi.section_id = ls.section_id AND lsi.library_name = ls.section_name ' \
                         'AND ls.is_active = 1 AND ls.deleted_section = 0 '

        try:
            if growth:
                query = 'SELECT ' \
                            '0 AS date_added, ' \
                            'SUM(CASE WHEN media_type = "movie" THEN 1 ELSE 0 END) AS movie_count, ' \
                            'SUM(CASE WHEN media_type = "show" THEN 1 ELSE 0 END) AS tv_count, ' \
                            'SUM(CASE WHEN media_type = "season" THEN 1 ELSE 0 END) AS season_count, ' \
                            'SUM(CASE WHEN media_type = "episode" THEN 1 ELSE 0 END) AS episode_count, ' \
                            'SUM(CASE WHEN media_type = "artist" THEN 1 ELSE 0 END) AS artist_count, ' \
                            'SUM(CASE WHEN media_type = "album" THEN 1 ELSE 0 END) AS album_count, ' \
                            'SUM(CASE WHEN media_type = "track" THEN 1 ELSE 0 END) AS track_count ' \
                        'FROM library_stats_items %s' \
                        'WHERE added_at < %s ' \
                        'UNION ALL ' \
                        'SELECT raM.date_added, ' \
                            'SUM(CASE WHEN raM.media_type = "movie" THEN 1 ELSE 0 END) AS movie_count, ' \
                            '0 AS tv_count, ' \
                            '0 AS season_count, ' \
                            'SUM(CASE WHEN raM.media_type = "episode" THEN 1 ELSE 0 END) AS episode_count, ' \
                            '0 AS artist_count, ' \
                            '0 AS album_count, ' \
                            'SUM(CASE WHEN raM.media_type = "track" THEN 1 ELSE 0 END) AS track_count ' \
                            'FROM (SELECT *, date(added_at, "unixepoch", "localtime") AS date_added ' \
                            '    FROM library_stats_items %s' \
                            '    WHERE (media_type = "movie" OR media_type = "episode" or media_type = "track") AND added_at >= %s) AS raM ' \
                        'GROUP BY raM.date_added ' \
                        'UNION ALL ' \
                        'SELECT raG.date_added, ' \
                            '0 AS movie_count, ' \
                            'SUM(CASE WHEN NOT raG.grandparent_rating_key = "" AND media_type = "episode" THEN 1 ELSE 0 END) AS tv_count, ' \
                            '0 AS season_count, ' \
                            '0 AS episode_count, ' \
                            'SUM(CASE WHEN NOT raG.grandparent_rating_key = "" AND media_type = "track" THEN 1 ELSE 0 END) AS artist_count, ' \
                            '0 AS album_count, ' \
                            '0 AS track_count ' \
                            'FROM (SELECT *, date(added_at, "unixepoch", "localtime") AS date_added ' \
                            '    FROM library_stats_items %s' \
                            '    WHERE NOT grandparent_rating_key = "" AND (media_type = "episode" OR media_type = "track") AND added_at >= %s ' \
                            '    GROUP BY grandparent_rating_key) AS raG ' \
                        'GROUP BY raG.date_added ' \
                        'UNION ALL ' \
                        'SELECT raS.date_added, ' \
                            '0 AS movie_count, ' \
                            '0 AS tv_count, ' \
                            'SUM(CASE WHEN NOT raS.parent_rating_key = "" AND media_type = "episode" THEN 1 ELSE 0 END) AS season_count, ' \
                            '0 AS episode_count, ' \
                            '0 AS artist_count, ' \
                            'SUM(CASE WHEN NOT raS.parent_rating_key = "" AND media_type = "track" THEN 1 ELSE 0 END) AS album_count, ' \
                            '0 AS track_count ' \
                            'FROM (SELECT *, date(added_at, "unixepoch", "localtime") AS date_added ' \
                            '   FROM library_stats_items %s' \
                            '   WHERE NOT parent_rating_key = "" AND (media_type = "episode" OR media_type = "track") AND added_at >= %s ' \
                            '   GROUP BY parent_rating_key) AS raS ' \
                        'GROUP BY raS.date_added ' \
                        'ORDER BY date_added' % (join_statement, timestamp,
                                                join_statement, timestamp,
                                                join_statement, timestamp,
                                                join_statement, timestamp)

                result = monitor_db.select(query)
            else:
                query = 'SELECT raM.date_added, ' \
                            'SUM(CASE WHEN raM.media_type = "movie" THEN 1 ELSE 0 END) AS movie_count, ' \
                            '0 AS tv_count, ' \
                            '0 AS season_count, ' \
                            'SUM(CASE WHEN raM.media_type = "episode" THEN 1 ELSE 0 END) AS episode_count, ' \
                            '0 AS artist_count, ' \
                            '0 AS album_count, ' \
                            'SUM(CASE WHEN raM.media_type = "track" THEN 1 ELSE 0 END) AS track_count ' \
                            'FROM (SELECT *, date(added_at, "unixepoch", "localtime") AS date_added ' \
                            '    FROM library_stats_items %s' \
                            '    WHERE (media_type = "movie" OR media_type = "episode" or media_type = "track") AND added_at >= %s) AS raM ' \
                        'GROUP BY raM.date_added ' \
                        'UNION ALL ' \
                        'SELECT raG.date_added, ' \
                            '0 AS movie_count, ' \
                            'SUM(CASE WHEN NOT raG.grandparent_rating_key = "" AND media_type = "episode" THEN 1 ELSE 0 END) AS tv_count, ' \
                            '0 AS season_count, ' \
                            '0 AS episode_count, ' \
                            'SUM(CASE WHEN NOT raG.grandparent_rating_key = "" AND media_type = "track" THEN 1 ELSE 0 END) AS artist_count, ' \
                            '0 AS album_count, ' \
                            '0 AS track_count ' \
                            'FROM (SELECT *, date(added_at, "unixepoch", "localtime") AS date_added ' \
                            '    FROM library_stats_items %s' \
                            '    WHERE NOT grandparent_rating_key = "" AND (media_type = "episode" OR media_type = "track") AND added_at >= %s ' \
                            '    GROUP BY grandparent_rating_key) AS raG ' \
                        'GROUP BY raG.date_added ' \
                        'UNION ALL ' \
                        'SELECT raS.date_added, ' \
                            '0 AS movie_count, ' \
                            '0 AS tv_count, ' \
                            'SUM(CASE WHEN NOT raS.parent_rating_key = "" AND media_type = "episode" THEN 1 ELSE 0 END) AS season_count, ' \
                            '0 AS episode_count, ' \
                            '0 AS artist_count, ' \
                            'SUM(CASE WHEN NOT raS.parent_rating_key = "" AND media_type = "track" THEN 1 ELSE 0 END) AS album_count, ' \
                            '0 AS track_count ' \
                            'FROM (SELECT *, date(added_at, "unixepoch", "localtime") AS date_added ' \
                            '   FROM library_stats_items %s' \
                            '   WHERE NOT parent_rating_key = "" AND (media_type = "episode" OR media_type = "track") AND added_at >= %s ' \
                            '   GROUP BY parent_rating_key) AS raS ' \
                        'GROUP BY raS.date_added ' \
                        'ORDER BY date_added' % (join_statement, timestamp,
                                                join_statement, timestamp,
                                                join_statement, timestamp)

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn("Tautulli Graphs :: Unable to execute database query for get_total_additions_per_day: %s." % e)
            return None

         # create our date range as some days may not have any data
        # but we still want to display them
        base = datetime.date.today()
        date_list = [base - datetime.timedelta(days=x) for x in range(0, int(time_range))]

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []
        series_4 = []
        series_5 = []
        series_6 = []
        series_7 = []

        if growth:
            base_value_1 = result[0]['movie_count'] if result[0]['movie_count'] else 0
            base_value_2 = result[0]['tv_count'] if result[0]['tv_count'] else 0
            base_value_3 = result[0]['season_count'] if result[0]['season_count'] else 0
            base_value_4 = result[0]['episode_count'] if result[0]['episode_count'] else 0
            base_value_5 = result[0]['artist_count'] if result[0]['artist_count'] else 0
            base_value_6 = result[0]['album_count'] if result[0]['album_count'] else 0
            base_value_7 = result[0]['track_count'] if result[0]['track_count'] else 0

        for date_item in sorted(date_list):
            date_string = date_item.strftime('%Y-%m-%d')
            categories.append(date_string)
            series_1_value = 0
            series_2_value = 0
            series_3_value = 0
            series_4_value = 0
            series_5_value = 0
            series_6_value = 0
            series_7_value = 0
            for item in result:
                if date_string == item['date_added']:
                    series_1_value = item['movie_count'] if series_1_value is 0 else series_1_value
                    series_2_value = item['tv_count'] if series_2_value is 0 else series_2_value
                    series_3_value = item['season_count'] if series_3_value is 0 else series_3_value
                    series_4_value = item['episode_count'] if series_4_value is 0 else series_4_value
                    series_5_value = item['artist_count'] if series_5_value is 0 else series_5_value
                    series_6_value = item['album_count'] if series_6_value is 0 else series_6_value
                    series_7_value = item['track_count'] if series_7_value is 0 else series_7_value
                    continue

            series_1.append(series_1_value)
            series_2.append(series_2_value)
            series_3.append(series_3_value)
            series_4.append(series_4_value)
            series_5.append(series_5_value)
            series_6.append(series_6_value)
            series_7.append(series_7_value)

        if growth:
            for idx, day in enumerate(series_1):
                series_1[idx] = base_value_1 + day
                base_value_1 += day
            for idx, day in enumerate(series_2):
                series_2[idx] = base_value_2 + day
                base_value_2 += day
            for idx, day in enumerate(series_3):
                series_3[idx] = base_value_3 + day
                base_value_3 += day
            for idx, day in enumerate(series_4):
                series_4[idx] = base_value_4 + day
                base_value_4 += day
            for idx, day in enumerate(series_5):
                series_5[idx] = base_value_5 + day
                base_value_5 += day
            for idx, day in enumerate(series_6):
                series_6[idx] = base_value_6 + day
                base_value_6 += day
            for idx, day in enumerate(series_7):
                series_7[idx] = base_value_7 + day
                base_value_7 += day

        series_1_output = {'name': 'Movies',
                           'data': series_1}
        series_2_output = {'name': 'Shows',
                           'data': series_2}
        series_3_output = {'name': 'Seasons',
                           'data': series_3}
        series_4_output = {'name': 'Episodes',
                           'data': series_4}
        series_5_output = {'name': 'Artists',
                           'data': series_5}
        series_6_output = {'name': 'Albums',
                           'data': series_6}
        series_7_output = {'name': 'Tracks',
                           'data': series_7}

        series_output = []
        if libraries.has_library_type('movie'):
            series_output.append(series_1_output)
        if libraries.has_library_type('show'):
            series_output.append(series_2_output)
            series_output.append(series_3_output)
            series_output.append(series_4_output)
        if libraries.has_library_type('artist'):
            series_output.append(series_5_output)
            series_output.append(series_6_output)
            series_output.append(series_7_output)

        output = {'categories': categories,
                  'series': series_output}
        
        return output

    def get_total_additions_by_media_type(self, time_range='30'):
        monitor_db = database.MonitorDatabase()

        time_range = helpers.cast_to_int(time_range) or 30
        timestamp = helpers.timestamp() - time_range * 24 * 60 * 60

        try:
            query = 'SELECT ' \
                        'SUM(CASE WHEN media_type = "movie" THEN 1 ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "show" THEN 1 ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "season" THEN 1 ELSE 0 END) AS season_count, ' \
                        'SUM(CASE WHEN media_type = "episode" THEN 1 ELSE 0 END) AS episode_count, ' \
                        'SUM(CASE WHEN media_type = "artist" THEN 1 ELSE 0 END) AS artist_count, ' \
                        'SUM(CASE WHEN media_type = "album" THEN 1 ELSE 0 END) AS album_count, ' \
                        'SUM(CASE WHEN media_type = "track" THEN 1 ELSE 0 END) AS track_count ' \
                    'FROM library_stats_items AS lsi JOIN library_sections AS ls ON ' \
	                    'lsi.section_id = ls.section_id AND lsi.library_name = ls.section_name ' \
                        'AND ls.is_active = 1 AND ls.deleted_section = 0 ' \
                    'WHERE added_at >= %s' % timestamp

            result = monitor_db.select(query)

        except Exception as e:
            logger.warn("Tautulli Graphs :: Unable to execute database query for get_total_additions_by_media_type: %s." % e)
            return None

        categories = ["Movies", "TV", "Music"]
        _catCount = len(categories)

        series_1 = [None] * _catCount
        series_2 = [None] * _catCount
        series_3 = [None] * _catCount
        series_4 = [None] * _catCount
        series_5 = [None] * _catCount
        series_6 = [None] * _catCount
        series_7 = [None] * _catCount

        content = result[0]

        for idx, item in enumerate(categories):
            if idx == 0:
                series_1[idx] = content['movie_count']
            elif idx == 1:
                series_2[idx] = content['tv_count']
                series_3[idx] = content['season_count']
                series_4[idx] = content['episode_count']
            else:
                series_5[idx] = content['artist_count']
                series_6[idx] = content['album_count']
                series_7[idx] = content['track_count']

        series_1_output = {'name': 'Movies',
                           'data': series_1}
        series_2_output = {'name': 'Shows',
                           'data': series_2}
        series_3_output = {'name': 'Seasons',
                           'data': series_3}
        series_4_output = {'name': 'Episodes',
                           'data': series_4}
        series_5_output = {'name': 'Artists',
                           'data': series_5}
        series_6_output = {'name': 'Albums',
                           'data': series_6}
        series_7_output = {'name': 'Tracks',
                           'data': series_7}

        series_output = []
        if libraries.has_library_type('movie'):
            series_output.append(series_1_output)
        if libraries.has_library_type('show'):
            series_output.append(series_2_output)
            series_output.append(series_3_output)
            series_output.append(series_4_output)
        if libraries.has_library_type('artist'):
            series_output.append(series_5_output)
            series_output.append(series_6_output)
            series_output.append(series_7_output)

        output = {'categories': categories,
                  'series': series_output}

        return output

    def get_total_additions_by_resolution(self, time_range='30'):
        monitor_db = database.MonitorDatabase()

        time_range = helpers.cast_to_int(time_range) or 30
        timestamp = helpers.timestamp() - time_range * 24 * 60 * 60

        resolution_identifier = '(CASE WHEN media_info LIKE \'%"video_resolution": "4K"%\' THEN "1_4K" ' \
                                'WHEN media_info LIKE \'%"video_resolution": "1080"%\' THEN "2_1080" ' \
                                'WHEN media_info LIKE \'%"video_resolution": "720"%\' THEN "3_720" ' \
                                'WHEN media_info LIKE \'%"video_resolution": "576"%\' THEN "4_576" ' \
                                'WHEN media_info LIKE \'%"video_resolution": "480"%\' THEN "5_480" ' \
                                'WHEN media_info LIKE \'%"video_resolution": "sd"%\' THEN "6_SD" ELSE "7_Unknown" END) AS resolution '

        join_statement = ' AS lsi JOIN library_sections AS ls ON ' \
	                     'lsi.section_id = ls.section_id AND lsi.library_name = ls.section_name ' \
                         'AND ls.is_active = 1 AND ls.deleted_section = 0 '

        try:
            query = 'SELECT ' \
                        'ra.resolution, ' \
                        'SUM(ra.movie_count) AS movie_count, ' \
                        'SUM(ra.tv_count) AS tv_count, ' \
                        'SUM(ra.season_count) AS season_count, ' \
                        'SUM(ra.episode_count) AS episode_count ' \
                    'FROM(' \
                        'SELECT ' \
                            'raM.resolution, ' \
                            'SUM(CASE WHEN raM.media_type = "movie" THEN 1 ELSE 0 END) AS movie_count, ' \
                            '0 AS tv_count, ' \
                            '0 AS season_count, ' \
                            'SUM(CASE WHEN raM.media_type = "episode" THEN 1 ELSE 0 END) AS episode_count ' \
                            'FROM (SELECT *, %s ' \
                                'FROM library_stats_items %s' \
                                'WHERE (media_type = "movie" OR media_type = "episode") AND added_at >= %s) AS raM ' \
                            'GROUP BY raM.resolution ' \
                        'UNION ALL ' \
                        'SELECT ' \
                            'raG.resolution, ' \
                            '0 AS movie_count, ' \
                            'SUM(CASE WHEN NOT raG.grandparent_rating_key = "" THEN 1 ELSE 0 END) AS tv_count, ' \
                            '0 AS season_count, ' \
                            '0 AS episode_count ' \
                            'FROM (SELECT *, %s ' \
                                'FROM library_stats_items %s' \
                            '    WHERE NOT grandparent_rating_key = "" AND media_type = "episode" AND added_at >= %s ' \
                            '    GROUP BY grandparent_rating_key) AS raG ' \
                            'GROUP BY raG.resolution ' \
                        'UNION ALL ' \
                        'SELECT ' \
                            'raS.resolution, ' \
                            '0 AS movie_count, ' \
                            '0 AS tv_count, ' \
                            'SUM(CASE WHEN NOT raS.parent_rating_key = "" THEN 1 ELSE 0 END) AS season_count, ' \
                            '0 AS episode_count ' \
                            'FROM (SELECT *, %s ' \
                                'FROM library_stats_items %s' \
                                'WHERE NOT parent_rating_key = "" AND media_type = "episode" AND added_at >= %s ' \
                                'GROUP BY parent_rating_key) AS raS ' \
                            'GROUP BY raS.resolution) AS ra ' \
                    'GROUP BY resolution ' \
                    'ORDER BY resolution' % (resolution_identifier, join_statement, timestamp,
                                            resolution_identifier, join_statement, timestamp,
                                            resolution_identifier, join_statement, timestamp)

            result = monitor_db.select(query)

        except Exception as e:
            logger.warn("Tautulli Graphs :: Unable to execute database query for get_total_additions_by_resolution: %s." % e)
            return None

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []
        series_4 = []

        for idx, item in enumerate(result):
            #remove sorting indicators (like 1_%)
            categories.append(item['resolution'][2:])

            series_1.append(item['movie_count'])
            series_2.append(item['tv_count'])
            series_3.append(item['season_count'])
            series_4.append(item['episode_count'])

        series_1_output = {'name': 'Movies',
                           'data': series_1}
        series_2_output = {'name': 'Shows',
                           'data': series_2}
        series_3_output = {'name': 'Seasons',
                           'data': series_3}
        series_4_output = {'name': 'Episodes',
                           'data': series_4}

        series_output = []
        if libraries.has_library_type('movie'):
            series_output.append(series_1_output)
        if libraries.has_library_type('show'):
            series_output.append(series_2_output)
            series_output.append(series_3_output)
            series_output.append(series_4_output)

        output = {'categories': categories,
                  'series': series_output}
        return output

    def get_total_plays_per_month(self, time_range='12', y_axis='plays', user_id=None, grouping=None):
        monitor_db = database.MonitorDatabase()

        time_range = helpers.cast_to_int(time_range) or 12
        timestamp = arrow.get(helpers.timestamp()).shift(months=-time_range).floor('month').timestamp

        user_cond = ''
        if session.get_session_user_id() and user_id and user_id != str(session.get_session_user_id()):
            user_cond = 'AND session_history.user_id = %s ' % session.get_session_user_id()
        elif user_id and user_id.isdigit():
            user_cond = 'AND session_history.user_id = %s ' % user_id

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        group_by = 'session_history.reference_id' if grouping else 'session_history.id'

        try:
            if y_axis == 'plays':
                query = 'SELECT sh.datestring, ' \
                        'SUM(CASE WHEN sh.media_type = "episode" AND shm.live = 0 THEN 1 ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN sh.media_type = "movie" AND shm.live = 0 THEN 1 ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN sh.media_type = "track" AND shm.live = 0 THEN 1 ELSE 0 END) AS music_count, ' \
                        'SUM(shm.live) AS live_count ' \
                        'FROM (SELECT *, ' \
                        '      strftime("%%Y-%%m", datetime(started, "unixepoch", "localtime")) AS datestring' \
                        '    FROM session_history ' \
                        '    WHERE session_history.stopped >= %s %s ' \
                        '    GROUP BY datestring, %s) AS sh ' \
                        'JOIN session_history_metadata AS shm ON shm.id = sh.id ' \
                        'GROUP BY sh.datestring ' \
                        'ORDER BY sh.datestring' % (timestamp, user_cond, group_by)

                result = monitor_db.select(query)
            else:
                query = 'SELECT sh.datestring, ' \
                        'SUM(CASE WHEN sh.media_type = "episode" AND shm.live = 0 ' \
                        '  THEN sh.d ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN sh.media_type = "movie" AND shm.live = 0 ' \
                        '  THEN sh.d ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN sh.media_type = "track" AND shm.live = 0 ' \
                        '  THEN sh.d ELSE 0 END) AS music_count, ' \
                        'SUM(CASE WHEN shm.live = 1 ' \
                        '  THEN sh.d ELSE 0 END) AS live_count ' \
                        'FROM (SELECT *, ' \
                        '      strftime("%%Y-%%m", datetime(started, "unixepoch", "localtime")) AS datestring, ' \
                        '      SUM(CASE WHEN stopped > 0 THEN (stopped - started) - ' \
                        '        (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) ' \
                        '        AS d ' \
                        '    FROM session_history ' \
                        '    WHERE session_history.stopped >= %s %s' \
                        '    GROUP BY datestring, %s) AS sh ' \
                        'JOIN session_history_metadata AS shm ON shm.id = sh.id ' \
                        'GROUP BY sh.datestring ' \
                        'ORDER BY sh.datestring' % (timestamp, user_cond, group_by)

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn("Tautulli Graphs :: Unable to execute database query for get_total_plays_per_month: %s." % e)
            return None

        # create our date range as some months may not have any data
        # but we still want to display them
        dt_today = datetime.date.today()
        dt = dt_today
        month_range = [dt]
        for n in range(int(time_range)-1):
            if not ((dt_today.month-n) % 12)-1:
                dt = datetime.date(dt.year-1, 12, 1)
            else:
                dt = datetime.date(dt.year, dt.month-1, 1)
            month_range.append(dt)

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []
        series_4 = []

        for dt in sorted(month_range):
            date_string = dt.strftime('%Y-%m')
            categories.append(dt.strftime('%b %Y'))
            series_1_value = 0
            series_2_value = 0
            series_3_value = 0
            series_4_value = 0
            for item in result:
                if date_string == item['datestring']:
                    series_1_value = item['tv_count']
                    series_2_value = item['movie_count']
                    series_3_value = item['music_count']
                    series_4_value = item['live_count']
                    break
                else:
                    series_1_value = 0
                    series_2_value = 0
                    series_3_value = 0
                    series_4_value = 0

            series_1.append(series_1_value)
            series_2.append(series_2_value)
            series_3.append(series_3_value)
            series_4.append(series_4_value)

        series_1_output = {'name': 'TV',
                           'data': series_1}
        series_2_output = {'name': 'Movies',
                           'data': series_2}
        series_3_output = {'name': 'Music',
                           'data': series_3}
        series_4_output = {'name': 'Live TV',
                           'data': series_4}

        series_output = []
        if libraries.has_library_type('show'):
            series_output.append(series_1_output)
        if libraries.has_library_type('movie'):
            series_output.append(series_2_output)
        if libraries.has_library_type('artist'):
            series_output.append(series_3_output)
        if libraries.has_library_type('live'):
            series_output.append(series_4_output)

        output = {'categories': categories,
                  'series': series_output}
        return output

    def get_total_plays_by_top_10_platforms(self, time_range='30', y_axis='plays', user_id=None, grouping=None):
        monitor_db = database.MonitorDatabase()

        time_range = helpers.cast_to_int(time_range) or 30
        timestamp = helpers.timestamp() - time_range * 24 * 60 * 60

        user_cond = ''
        if session.get_session_user_id() and user_id and user_id != str(session.get_session_user_id()):
            user_cond = 'AND session_history.user_id = %s ' % session.get_session_user_id()
        elif user_id and user_id.isdigit():
            user_cond = 'AND session_history.user_id = %s ' % user_id

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        group_by = 'session_history.reference_id' if grouping else 'session_history.id'

        try:
            if y_axis == 'plays':
                query = 'SELECT sh.platform, ' \
                        'SUM(CASE WHEN sh.media_type = "episode" AND shm.live = 0 THEN 1 ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN sh.media_type = "movie" AND shm.live = 0 THEN 1 ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN sh.media_type = "track" AND shm.live = 0 THEN 1 ELSE 0 END) AS music_count, ' \
                        'SUM(shm.live) AS live_count, ' \
                        'COUNT(sh.id) AS total_count ' \
                        'FROM (SELECT * ' \
                        '    FROM session_history ' \
                        '    WHERE session_history.stopped >= %s %s ' \
                        '    GROUP BY %s) AS sh ' \
                        'JOIN session_history_metadata AS shm ON shm.id = sh.id ' \
                        'GROUP BY sh.platform ' \
                        'ORDER BY total_count DESC, sh.platform ASC ' \
                        'LIMIT 10' % (timestamp, user_cond, group_by)

                result = monitor_db.select(query)
            else:
                query = 'SELECT sh.platform, ' \
                        'SUM(CASE WHEN sh.media_type = "episode" AND shm.live = 0 ' \
                        '  THEN sh.d ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN sh.media_type = "movie" AND shm.live = 0 ' \
                        '  THEN sh.d ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN sh.media_type = "track" AND shm.live = 0 ' \
                        '  THEN sh.d ELSE 0 END) AS music_count, ' \
                        'SUM(CASE WHEN shm.live = 1 ' \
                        '  THEN sh.d ELSE 0 END) AS live_count, ' \
                        'SUM(sh.d) AS total_duration ' \
                        'FROM (SELECT *, ' \
                        '      SUM(CASE WHEN stopped > 0 THEN (stopped - started) - ' \
                        '        (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) ' \
                        '        AS d ' \
                        '    FROM session_history ' \
                        '    WHERE session_history.stopped >= %s %s' \
                        '    GROUP BY %s) AS sh ' \
                        'JOIN session_history_metadata AS shm ON shm.id = sh.id ' \
                        'GROUP BY sh.platform ' \
                        'ORDER BY total_duration DESC ' \
                        'LIMIT 10' % (timestamp, user_cond, group_by)

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn("Tautulli Graphs :: Unable to execute database query for get_total_plays_by_top_10_platforms: %s." % e)
            return None

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []
        series_4 = []

        for item in result:
            categories.append(common.PLATFORM_NAME_OVERRIDES.get(item['platform'], item['platform']))
            series_1.append(item['tv_count'])
            series_2.append(item['movie_count'])
            series_3.append(item['music_count'])
            series_4.append(item['live_count'])

        series_1_output = {'name': 'TV',
                           'data': series_1}
        series_2_output = {'name': 'Movies',
                           'data': series_2}
        series_3_output = {'name': 'Music',
                           'data': series_3}
        series_4_output = {'name': 'Live TV',
                           'data': series_4}

        series_output = []
        if libraries.has_library_type('show'):
            series_output.append(series_1_output)
        if libraries.has_library_type('movie'):
            series_output.append(series_2_output)
        if libraries.has_library_type('artist'):
            series_output.append(series_3_output)
        if libraries.has_library_type('live'):
            series_output.append(series_4_output)

        output = {'categories': categories,
                  'series': series_output}
        return output

    def get_total_plays_by_top_10_users(self, time_range='30', y_axis='plays', user_id=None, grouping=None):
        monitor_db = database.MonitorDatabase()

        time_range = helpers.cast_to_int(time_range) or 30
        timestamp = helpers.timestamp() - time_range * 24 * 60 * 60

        user_cond = ''
        if session.get_session_user_id() and user_id and user_id != str(session.get_session_user_id()):
            user_cond = 'AND session_history.user_id = %s ' % session.get_session_user_id()
        elif user_id and user_id.isdigit():
            user_cond = 'AND session_history.user_id = %s ' % user_id

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        group_by = 'session_history.reference_id' if grouping else 'session_history.id'

        try:
            if y_axis == 'plays':
                query = 'SELECT u.user_id, u.username, ' \
                        '(CASE WHEN u.friendly_name IS NULL OR TRIM(u.friendly_name) = "" ' \
                        '  THEN u.username ELSE u.friendly_name END) AS friendly_name,' \
                        'SUM(CASE WHEN sh.media_type = "episode" AND shm.live = 0 THEN 1 ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN sh.media_type = "movie" AND shm.live = 0 THEN 1 ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN sh.media_type = "track" AND shm.live = 0 THEN 1 ELSE 0 END) AS music_count, ' \
                        'SUM(shm.live) AS live_count, ' \
                        'COUNT(sh.id) AS total_count ' \
                        'FROM (SELECT * ' \
                        '    FROM session_history ' \
                        '    WHERE session_history.stopped >= %s %s ' \
                        '    GROUP BY %s) AS sh ' \
                        'JOIN session_history_metadata AS shm ON shm.id = sh.id ' \
                        'JOIN users AS u ON u.user_id = sh.user_id ' \
                        'GROUP BY sh.user_id ' \
                        'ORDER BY total_count DESC ' \
                        'LIMIT 10' % (timestamp, user_cond, group_by)

                result = monitor_db.select(query)
            else:
                query = 'SELECT u.user_id, u.username, ' \
                        '(CASE WHEN u.friendly_name IS NULL OR TRIM(u.friendly_name) = "" ' \
                        ' THEN u.username ELSE u.friendly_name END) AS friendly_name,' \
                        'SUM(CASE WHEN sh.media_type = "episode" AND shm.live = 0 ' \
                        '  THEN sh.d ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN sh.media_type = "movie" AND shm.live = 0 ' \
                        '  THEN sh.d ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN sh.media_type = "track" AND shm.live = 0 ' \
                        '  THEN sh.d ELSE 0 END) AS music_count, ' \
                        'SUM(CASE WHEN shm.live = 1 ' \
                        '  THEN sh.d ELSE 0 END) AS live_count, ' \
                        'SUM(sh.d) AS total_duration ' \
                        'FROM (SELECT *, ' \
                        '      SUM(CASE WHEN stopped > 0 THEN (stopped - started) - ' \
                        '         (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) ' \
                        '         AS d ' \
                        '    FROM session_history ' \
                        '    WHERE session_history.stopped >= %s %s' \
                        '    GROUP BY %s) AS sh ' \
                        'JOIN session_history_metadata AS shm ON shm.id = sh.id ' \
                        'JOIN users AS u ON u.user_id = sh.user_id ' \
                        'GROUP BY sh.user_id ' \
                        'ORDER BY total_duration DESC ' \
                        'LIMIT 10' % (timestamp, user_cond, group_by)

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn("Tautulli Graphs :: Unable to execute database query for get_total_plays_by_top_10_users: %s." % e)
            return None

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []
        series_4 = []

        session_user_id = session.get_session_user_id()

        for item in result:
            if session_user_id:
                categories.append(item['username'] if str(item['user_id']) == session_user_id else 'Plex User')
            else:
                categories.append(item['friendly_name'])
            series_1.append(item['tv_count'])
            series_2.append(item['movie_count'])
            series_3.append(item['music_count'])
            series_4.append(item['live_count'])

        series_1_output = {'name': 'TV',
                           'data': series_1}
        series_2_output = {'name': 'Movies',
                           'data': series_2}
        series_3_output = {'name': 'Music',
                           'data': series_3}
        series_4_output = {'name': 'Live TV',
                           'data': series_4}

        series_output = []
        if libraries.has_library_type('show'):
            series_output.append(series_1_output)
        if libraries.has_library_type('movie'):
            series_output.append(series_2_output)
        if libraries.has_library_type('artist'):
            series_output.append(series_3_output)
        if libraries.has_library_type('live'):
            series_output.append(series_4_output)

        output = {'categories': categories,
                  'series': series_output}
        return output

    def get_total_plays_per_stream_type(self, time_range='30', y_axis='plays', user_id=None, grouping=None):
        monitor_db = database.MonitorDatabase()

        time_range = helpers.cast_to_int(time_range) or 30
        timestamp = helpers.timestamp() - time_range * 24 * 60 * 60

        user_cond = ''
        if session.get_session_user_id() and user_id and user_id != str(session.get_session_user_id()):
            user_cond = 'AND session_history.user_id = %s ' % session.get_session_user_id()
        elif user_id and user_id.isdigit():
            user_cond = 'AND session_history.user_id = %s ' % user_id

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        group_by = 'session_history.reference_id' if grouping else 'session_history.id'

        try:
            if y_axis == 'plays':
                query = 'SELECT sh.date_played, ' \
                        'SUM(CASE WHEN shmi.transcode_decision = "direct play" THEN 1 ELSE 0 END) AS dp_count, ' \
                        'SUM(CASE WHEN shmi.transcode_decision = "copy" THEN 1 ELSE 0 END) AS ds_count, ' \
                        'SUM(CASE WHEN shmi.transcode_decision = "transcode" THEN 1 ELSE 0 END) AS tc_count ' \
                        'FROM (SELECT *, ' \
                        '      date(started, "unixepoch", "localtime") AS date_played ' \
                        '    FROM session_history ' \
                        '    WHERE session_history.stopped >= %s %s ' \
                        '    GROUP BY date_played, %s) AS sh ' \
                        'JOIN session_history_media_info AS shmi ON shmi.id = sh.id ' \
                        'GROUP BY sh.date_played ' \
                        'ORDER BY sh.started' % (timestamp, user_cond, group_by)

                result = monitor_db.select(query)
            else:
                query = 'SELECT sh.date_played, ' \
                        'SUM(CASE WHEN shmi.transcode_decision = "direct play" THEN sh.d ELSE 0 END) AS dp_count, ' \
                        'SUM(CASE WHEN shmi.transcode_decision = "copy" THEN sh.d ELSE 0 END) AS ds_count, ' \
                        'SUM(CASE WHEN shmi.transcode_decision = "transcode" THEN sh.d ELSE 0 END) AS tc_count ' \
                        'FROM (SELECT *, ' \
                        '      date(started, "unixepoch", "localtime") AS date_played,' \
                        '      SUM(CASE WHEN stopped > 0 THEN (stopped - started) - ' \
                        '        (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) ' \
                        '        AS d ' \
                        '    FROM session_history ' \
                        '    WHERE session_history.stopped >= %s %s' \
                        '    GROUP BY date_played, %s) AS sh ' \
                        'JOIN session_history_media_info AS shmi ON shmi.id = sh.id ' \
                        'GROUP BY sh.date_played ' \
                        'ORDER BY sh.started' % (timestamp, user_cond, group_by)

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn("Tautulli Graphs :: Unable to execute database query for get_total_plays_per_stream_type: %s." % e)
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

    def get_total_plays_by_source_resolution(self, time_range='30', y_axis='plays', user_id=None, grouping=None):
        monitor_db = database.MonitorDatabase()

        time_range = helpers.cast_to_int(time_range) or 30
        timestamp = helpers.timestamp() - time_range * 24 * 60 * 60

        user_cond = ''
        if session.get_session_user_id() and user_id and user_id != str(session.get_session_user_id()):
            user_cond = 'AND session_history.user_id = %s ' % session.get_session_user_id()
        elif user_id and user_id.isdigit():
            user_cond = 'AND session_history.user_id = %s ' % user_id

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        group_by = 'session_history.reference_id' if grouping else 'session_history.id'

        try:
            if y_axis == 'plays':
                query = 'SELECT shmi.video_full_resolution AS resolution, ' \
                        'SUM(CASE WHEN shmi.transcode_decision = "direct play" THEN 1 ELSE 0 END) AS dp_count, ' \
                        'SUM(CASE WHEN shmi.transcode_decision = "copy" THEN 1 ELSE 0 END) AS ds_count, ' \
                        'SUM(CASE WHEN shmi.transcode_decision = "transcode" THEN 1 ELSE 0 END) AS tc_count, ' \
                        'COUNT(sh.id) AS total_count ' \
                        'FROM (SELECT * ' \
                        '    FROM session_history ' \
                        '    WHERE session_history.stopped >= %s ' \
                        '    AND session_history.media_type IN ("movie", "episode") %s ' \
                        '    GROUP BY %s) AS sh ' \
                        'JOIN session_history_media_info AS shmi ON shmi.id = sh.id ' \
                        'GROUP BY resolution ' \
                        'ORDER BY total_count DESC ' \
                        'LIMIT 10' % (timestamp, user_cond, group_by)

                result = monitor_db.select(query)
            else:
                query = 'SELECT shmi.video_full_resolution AS resolution,' \
                        'SUM(CASE WHEN shmi.transcode_decision = "direct play" THEN sh.d ELSE 0 END) AS dp_count, ' \
                        'SUM(CASE WHEN shmi.transcode_decision = "copy" THEN sh.d ELSE 0 END) AS ds_count, ' \
                        'SUM(CASE WHEN shmi.transcode_decision = "transcode" THEN sh.d ELSE 0 END) AS tc_count, ' \
                        'SUM(sh.d) AS total_duration ' \
                        'FROM (SELECT *, ' \
                        '      SUM(CASE WHEN stopped > 0 THEN (stopped - started) - ' \
                        '        (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) ' \
                        '        AS d ' \
                        '    FROM session_history ' \
                        '    WHERE session_history.stopped >= %s ' \
                        '    AND session_history.media_type IN ("movie", "episode") %s ' \
                        '    GROUP BY %s) AS sh ' \
                        'JOIN session_history_media_info AS shmi ON shmi.id = sh.id ' \
                        'GROUP BY resolution ' \
                        'ORDER BY total_duration DESC ' \
                        'LIMIT 10' % (timestamp, user_cond, group_by)

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn("Tautulli Graphs :: Unable to execute database query for get_total_plays_by_source_resolution: %s." % e)
            return None

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []

        for item in result:
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

    def get_total_plays_by_stream_resolution(self, time_range='30', y_axis='plays', user_id=None, grouping=None):
        monitor_db = database.MonitorDatabase()

        time_range = helpers.cast_to_int(time_range) or 30
        timestamp = helpers.timestamp() - time_range * 24 * 60 * 60

        user_cond = ''
        if session.get_session_user_id() and user_id and user_id != str(session.get_session_user_id()):
            user_cond = 'AND session_history.user_id = %s ' % session.get_session_user_id()
        elif user_id and user_id.isdigit():
            user_cond = 'AND session_history.user_id = %s ' % user_id

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        group_by = 'session_history.reference_id' if grouping else 'session_history.id'

        try:
            if y_axis == 'plays':
                query = 'SELECT ' \
                        '(CASE WHEN shmi.stream_video_full_resolution IS NULL THEN ' \
                        '  (CASE WHEN shmi.video_decision = "transcode" THEN ' \
                        '    (CASE ' \
                        '      WHEN shmi.transcode_height <= 360 THEN "SD" ' \
                        '      WHEN shmi.transcode_height <= 480 THEN "480" ' \
                        '      WHEN shmi.transcode_height <= 576 THEN "576" ' \
                        '      WHEN shmi.transcode_height <= 720 THEN "720" ' \
                        '      WHEN shmi.transcode_height <= 1080 THEN "1080" ' \
                        '      WHEN shmi.transcode_height <= 1440 THEN "QHD" ' \
                        '      WHEN shmi.transcode_height <= 2160 THEN "4k" ' \
                        '      ELSE "unknown" END)' \
                        '    ELSE shmi.video_full_resolution END) ' \
                        '  ELSE shmi.stream_video_full_resolution END) AS resolution, ' \
                        'SUM(CASE WHEN shmi.transcode_decision = "direct play" THEN 1 ELSE 0 END) AS dp_count, ' \
                        'SUM(CASE WHEN shmi.transcode_decision = "copy" THEN 1 ELSE 0 END) AS ds_count, ' \
                        'SUM(CASE WHEN shmi.transcode_decision = "transcode" THEN 1 ELSE 0 END) AS tc_count, ' \
                        'COUNT(sh.id) AS total_count ' \
                        'FROM (SELECT * ' \
                        '    FROM session_history ' \
                        '    WHERE session_history.stopped >= %s ' \
                        '    AND session_history.media_type IN ("movie", "episode") %s ' \
                        '    GROUP BY %s) AS sh ' \
                        'JOIN session_history_media_info AS shmi ON shmi.id = sh.id ' \
                        'GROUP BY resolution ' \
                        'ORDER BY total_count DESC ' \
                        'LIMIT 10' % (timestamp, user_cond, group_by)

                result = monitor_db.select(query)
            else:
                query = 'SELECT ' \
                        '(CASE WHEN shmi.stream_video_full_resolution IS NULL THEN ' \
                        '  (CASE WHEN shmi.video_decision = "transcode" THEN ' \
                        '    (CASE ' \
                        '      WHEN shmi.transcode_height <= 360 THEN "SD" ' \
                        '      WHEN shmi.transcode_height <= 480 THEN "480" ' \
                        '      WHEN shmi.transcode_height <= 576 THEN "576" ' \
                        '      WHEN shmi.transcode_height <= 720 THEN "720" ' \
                        '      WHEN shmi.transcode_height <= 1080 THEN "1080" ' \
                        '      WHEN shmi.transcode_height <= 1440 THEN "QHD" ' \
                        '      WHEN shmi.transcode_height <= 2160 THEN "4k" ' \
                        '      ELSE "unknown" END)' \
                        '    ELSE shmi.video_full_resolution END) ' \
                        '  ELSE shmi.stream_video_full_resolution END) AS resolution, ' \
                        'SUM(CASE WHEN shmi.transcode_decision = "direct play" THEN sh.d ELSE 0 END) AS dp_count, ' \
                        'SUM(CASE WHEN shmi.transcode_decision = "copy" THEN sh.d ELSE 0 END) AS ds_count, ' \
                        'SUM(CASE WHEN shmi.transcode_decision = "transcode" THEN sh.d ELSE 0 END) AS tc_count, ' \
                        'SUM(sh.d) AS total_duration ' \
                        'FROM (SELECT *, ' \
                        '      SUM(CASE WHEN stopped > 0 THEN (stopped - started) - ' \
                        '        (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) ' \
                        '        AS d ' \
                        '    FROM session_history ' \
                        '    WHERE session_history.stopped >= %s ' \
                        '    AND session_history.media_type IN ("movie", "episode") %s ' \
                        '    GROUP BY %s) AS sh ' \
                        'JOIN session_history_media_info AS shmi ON shmi.id = sh.id ' \
                        'GROUP BY resolution ' \
                        'ORDER BY total_duration DESC ' \
                        'LIMIT 10' % (timestamp, user_cond, group_by)

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn("Tautulli Graphs :: Unable to execute database query for get_total_plays_by_stream_resolution: %s." % e)
            return None

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []

        for item in result:
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

    def get_stream_type_by_top_10_platforms(self, time_range='30', y_axis='plays', user_id=None, grouping=None):
        monitor_db = database.MonitorDatabase()

        time_range = helpers.cast_to_int(time_range) or 30
        timestamp = helpers.timestamp() - time_range * 24 * 60 * 60

        user_cond = ''
        if session.get_session_user_id() and user_id and user_id != str(session.get_session_user_id()):
            user_cond = 'AND session_history.user_id = %s ' % session.get_session_user_id()
        elif user_id and user_id.isdigit():
            user_cond = 'AND session_history.user_id = %s ' % user_id

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        group_by = 'session_history.reference_id' if grouping else 'session_history.id'

        try:
            if y_axis == 'plays':
                query = 'SELECT sh.platform, ' \
                        'SUM(CASE WHEN shmi.transcode_decision = "direct play" THEN 1 ELSE 0 END) AS dp_count, ' \
                        'SUM(CASE WHEN shmi.transcode_decision = "copy" THEN 1 ELSE 0 END) AS ds_count, ' \
                        'SUM(CASE WHEN shmi.transcode_decision = "transcode" THEN 1 ELSE 0 END) AS tc_count, ' \
                        'COUNT(sh.id) AS total_count ' \
                        'FROM (SELECT * ' \
                        '    FROM session_history ' \
                        '    WHERE session_history.stopped >= %s %s ' \
                        '    GROUP BY %s) AS sh ' \
                        'JOIN session_history_media_info AS shmi ON shmi.id = sh.id ' \
                        'GROUP BY sh.platform ' \
                        'ORDER BY total_count DESC ' \
                        'LIMIT 10' % (timestamp, user_cond, group_by)

                result = monitor_db.select(query)
            else:
                query = 'SELECT sh.platform, ' \
                        'SUM(CASE WHEN shmi.transcode_decision = "direct play" THEN sh.d ELSE 0 END) AS dp_count, ' \
                        'SUM(CASE WHEN shmi.transcode_decision = "copy" THEN sh.d ELSE 0 END) AS ds_count, ' \
                        'SUM(CASE WHEN shmi.transcode_decision = "transcode" THEN sh.d ELSE 0 END) AS tc_count, ' \
                        'SUM(sh.d) AS total_duration ' \
                        'FROM (SELECT *, ' \
                        '      SUM(CASE WHEN stopped > 0 THEN (stopped - started) - ' \
                        '        (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) ' \
                        '        AS d ' \
                        '    FROM session_history ' \
                        '    WHERE session_history.stopped >= %s %s ' \
                        '    GROUP BY %s) AS sh ' \
                        'JOIN session_history_media_info AS shmi ON shmi.id = sh.id ' \
                        'GROUP BY sh.platform ' \
                        'ORDER BY total_duration DESC ' \
                        'LIMIT 10' % (timestamp, user_cond, group_by)

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn("Tautulli Graphs :: Unable to execute database query for get_stream_type_by_top_10_platforms: %s." % e)
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

    def get_stream_type_by_top_10_users(self, time_range='30', y_axis='plays', user_id=None, grouping=None):
        monitor_db = database.MonitorDatabase()

        time_range = helpers.cast_to_int(time_range) or 30
        timestamp = helpers.timestamp() - time_range * 24 * 60 * 60

        user_cond = ''
        if session.get_session_user_id() and user_id and user_id != str(session.get_session_user_id()):
            user_cond = 'AND session_history.user_id = %s ' % session.get_session_user_id()
        elif user_id and user_id.isdigit():
            user_cond = 'AND session_history.user_id = %s ' % user_id

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        group_by = 'session_history.reference_id' if grouping else 'session_history.id'

        try:
            if y_axis == 'plays':
                query = 'SELECT u.user_id, u.username, ' \
                        '(CASE WHEN u.friendly_name IS NULL OR TRIM(u.friendly_name) = "" ' \
                        '  THEN u.username ELSE u.friendly_name END) AS friendly_name,' \
                        'SUM(CASE WHEN shmi.transcode_decision = "direct play" THEN 1 ELSE 0 END) AS dp_count, ' \
                        'SUM(CASE WHEN shmi.transcode_decision = "copy" THEN 1 ELSE 0 END) AS ds_count, ' \
                        'SUM(CASE WHEN shmi.transcode_decision = "transcode" THEN 1 ELSE 0 END) AS tc_count, ' \
                        'COUNT(sh.id) AS total_count ' \
                        'FROM (SELECT * ' \
                        '    FROM session_history ' \
                        '    WHERE session_history.stopped >= %s %s ' \
                        '    GROUP BY %s) AS sh ' \
                        'JOIN session_history_media_info AS shmi ON shmi.id = sh.id ' \
                        'JOIN users AS u ON u.user_id = sh.user_id ' \
                        'GROUP BY u.user_id ' \
                        'ORDER BY total_count DESC ' \
                        'LIMIT 10' % (timestamp, user_cond, group_by)

                result = monitor_db.select(query)
            else:
                query = 'SELECT u.user_id, u.username, ' \
                        '(CASE WHEN u.friendly_name IS NULL OR TRIM(u.friendly_name) = "" ' \
                        '  THEN u.username ELSE u.friendly_name END) AS friendly_name,' \
                        'SUM(CASE WHEN shmi.transcode_decision = "direct play" THEN sh.d ELSE 0 END) AS dp_count, ' \
                        'SUM(CASE WHEN shmi.transcode_decision = "copy" THEN sh.d ELSE 0 END) AS ds_count, ' \
                        'SUM(CASE WHEN shmi.transcode_decision = "transcode" THEN sh.d ELSE 0 END) AS tc_count, ' \
                        'SUM(sh.d) AS total_duration ' \
                        'FROM (SELECT *, ' \
                        '      SUM(CASE WHEN stopped > 0 THEN (stopped - started) - ' \
                        '        (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) ' \
                        '        AS d ' \
                        '    FROM session_history ' \
                        '    WHERE session_history.stopped >= %s %s ' \
                        '    GROUP BY %s) AS sh ' \
                        'JOIN session_history_media_info AS shmi ON shmi.id = sh.id ' \
                        'JOIN users AS u ON u.user_id = sh.user_id ' \
                        'GROUP BY u.user_id ' \
                        'ORDER BY total_duration DESC ' \
                        'LIMIT 10' % (timestamp, user_cond, group_by)

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn("Tautulli Graphs :: Unable to execute database query for get_stream_type_by_top_10_users: %s." % e)
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
