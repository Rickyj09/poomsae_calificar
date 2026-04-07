from .academia import Academia
from .user import User
from .alumno import Alumno
from .video import Video
from .evaluacion import Evaluacion
from .evaluacion_item import EvaluacionItem
from app.models.poomsae import Poomsae
from app.models.video_patron import VideoPatron

__all__ = ["Academia", "User","Alumno","Video","Evaluacion", "EvaluacionItem", "Poomsae","VideoPatron"]