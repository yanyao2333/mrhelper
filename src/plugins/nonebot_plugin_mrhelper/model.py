from typing import Optional

from pydantic import Extra, BaseModel


class Config(BaseModel, extra=Extra.ignore):
    mrhelper_mrurl: Optional[str]
    mrhelper_embyurl: Optional[str] = None
    mrhelper_embyapikey: Optional[str] = None
    mrhelper_enable_registeremby: Optional[bool] = False
    mrhelper_enable_pushnotify: Optional[bool] = False
    superusers: Optional[list]
    command_start: Optional[list]
    mrhelper_autoaddfriend: Optional[bool] = True


class MediaInfo(BaseModel, extra=Extra.ignore):
    name: str
    type: str
    poster_url: str
    imdb_id: Optional[str] = "未知"
    have_chi_subtitle: bool = False
    air_process: Optional[str]  # 我也不知道咋命名了 反正内容就是“x季 有x集/全x集”
    overview: str
    next_episode_to_air_date: Optional[str]
    next_episode_to_air_index: Optional[str]
    genres: str
    release_date: str
