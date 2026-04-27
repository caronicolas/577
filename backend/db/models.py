from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Organe(Base):
    """Groupe parlementaire ou commission."""

    __tablename__ = "organes"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # ex: PO800520
    sigle: Mapped[str] = mapped_column(String(20))
    libelle: Mapped[str] = mapped_column(String(500))
    couleur: Mapped[Optional[str]] = mapped_column(String(7))  # hex #rrggbb
    legislature: Mapped[int] = mapped_column(Integer, default=17)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    deputes: Mapped[list["Depute"]] = relationship(back_populates="groupe")


class Depute(Base):
    """Député en exercice ou ancien député."""

    __tablename__ = "deputes"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # ex: PA1234
    nom: Mapped[str] = mapped_column(String(200))
    prenom: Mapped[str] = mapped_column(String(100))
    nom_de_famille: Mapped[str] = mapped_column(String(100))
    sexe: Mapped[Optional[str]] = mapped_column(String(1))
    date_naissance: Mapped[Optional[date]] = mapped_column(Date)
    profession: Mapped[Optional[str]] = mapped_column(String(200))
    num_departement: Mapped[Optional[str]] = mapped_column(String(3))
    nom_circonscription: Mapped[Optional[str]] = mapped_column(String(200))
    num_circonscription: Mapped[Optional[int]] = mapped_column(Integer)
    place_hemicycle: Mapped[Optional[int]] = mapped_column(Integer)
    url_photo: Mapped[Optional[str]] = mapped_column(String(500))
    url_an: Mapped[Optional[str]] = mapped_column(String(500))
    twitter: Mapped[Optional[str]] = mapped_column(String(100))
    facebook_url: Mapped[Optional[str]] = mapped_column(String(500))
    instagram_url: Mapped[Optional[str]] = mapped_column(String(500))
    bluesky_url: Mapped[Optional[str]] = mapped_column(String(500))
    mandat_debut: Mapped[Optional[date]] = mapped_column(Date)
    mandat_fin: Mapped[Optional[date]] = mapped_column(Date)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)
    legislature: Mapped[int] = mapped_column(Integer, default=17)
    groupe_id: Mapped[Optional[str]] = mapped_column(ForeignKey("organes.id"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    groupe: Mapped[Optional["Organe"]] = relationship(back_populates="deputes")
    votes: Mapped[list["VoteDepute"]] = relationship(back_populates="depute")
    amendements: Mapped[list["Amendement"]] = relationship(back_populates="depute")
    presences_commission: Mapped[list["PresenceCommission"]] = relationship(
        back_populates="depute"
    )


class Seance(Base):
    """Séance plénière (AN ou Sénat)."""

    __tablename__ = "seances"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)  # uid AN
    date: Mapped[date] = mapped_column(Date, index=True)
    titre: Mapped[Optional[str]] = mapped_column(Text)
    # ex: SéancePublique, SéanceOrdre
    type_seance: Mapped[Optional[str]] = mapped_column(String(50))
    is_senat: Mapped[bool] = mapped_column(Boolean, default=False)
    legislature: Mapped[int] = mapped_column(Integer, default=17)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    points_odj: Mapped[list["PointODJ"]] = relationship(back_populates="seance")
    scrutins: Mapped[list["Scrutin"]] = relationship(back_populates="seance")


class PointODJ(Base):
    """Point à l'ordre du jour d'une séance."""

    __tablename__ = "points_odj"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    seance_id: Mapped[str] = mapped_column(ForeignKey("seances.id"), index=True)
    ordre: Mapped[Optional[int]] = mapped_column(Integer)
    titre: Mapped[Optional[str]] = mapped_column(Text)

    seance: Mapped["Seance"] = relationship(back_populates="points_odj")


class ReunionCommission(Base):
    """Réunion de commission (AN ou Sénat)."""

    __tablename__ = "reunions_commission"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)  # uid AN
    date: Mapped[date] = mapped_column(Date, index=True)
    heure_debut: Mapped[Optional[str]] = mapped_column(String(10))
    heure_fin: Mapped[Optional[str]] = mapped_column(String(10))
    titre: Mapped[Optional[str]] = mapped_column(Text)
    organe_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("organes.id"), nullable=True
    )
    organe_libelle: Mapped[Optional[str]] = mapped_column(String(300))
    is_senat: Mapped[bool] = mapped_column(Boolean, default=False)
    legislature: Mapped[int] = mapped_column(Integer, default=17)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    presences: Mapped[list["PresenceCommission"]] = relationship(
        back_populates="reunion"
    )


class PresenceCommission(Base):
    """Présence d'un député à une réunion de commission."""

    __tablename__ = "presences_commission"

    reunion_id: Mapped[str] = mapped_column(
        ForeignKey("reunions_commission.id"), primary_key=True
    )
    depute_id: Mapped[str] = mapped_column(
        ForeignKey("deputes.id"), primary_key=True, index=True
    )

    reunion: Mapped["ReunionCommission"] = relationship(back_populates="presences")
    depute: Mapped["Depute"] = relationship(back_populates="presences_commission")


class Scrutin(Base):
    """Scrutin (vote solennel ou ordinaire)."""

    __tablename__ = "scrutins"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # ex: VTANR5L17V1234
    numero: Mapped[int] = mapped_column(Integer)
    titre: Mapped[str] = mapped_column(Text)
    date_seance: Mapped[date] = mapped_column(Date, index=True)
    type_vote: Mapped[Optional[str]] = mapped_column(String(50))
    sort: Mapped[Optional[str]] = mapped_column(String(20))  # adopté / rejeté
    nombre_votants: Mapped[Optional[int]] = mapped_column(Integer)
    nombre_pours: Mapped[Optional[int]] = mapped_column(Integer)
    nombre_contres: Mapped[Optional[int]] = mapped_column(Integer)
    nombre_abstentions: Mapped[Optional[int]] = mapped_column(Integer)
    url_an: Mapped[Optional[str]] = mapped_column(String(500))
    ref_amendement: Mapped[Optional[str]] = mapped_column(String(50))
    objet_libelle: Mapped[Optional[str]] = mapped_column(Text)
    dossier_ref: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    dossier_libelle: Mapped[Optional[str]] = mapped_column(Text)
    bluesky_posted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    seance_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("seances.id"), nullable=True, index=True
    )
    legislature: Mapped[int] = mapped_column(Integer, default=17)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    votes: Mapped[list["VoteDepute"]] = relationship(back_populates="scrutin")
    seance: Mapped[Optional["Seance"]] = relationship(back_populates="scrutins")


class VoteDepute(Base):
    """Vote d'un député sur un scrutin."""

    __tablename__ = "votes_deputes"

    scrutin_id: Mapped[str] = mapped_column(ForeignKey("scrutins.id"), primary_key=True)
    depute_id: Mapped[str] = mapped_column(ForeignKey("deputes.id"), primary_key=True)
    position: Mapped[str] = mapped_column(
        String(20)
    )  # pour / contre / abstention / nonVotant

    scrutin: Mapped["Scrutin"] = relationship(back_populates="votes")
    depute: Mapped["Depute"] = relationship(back_populates="votes")


class DatanDepute(Base):
    """Scores Datan par député (source : data.gouv.fr / Datan)."""

    __tablename__ = "datan_deputes"

    identifiant_an: Mapped[str] = mapped_column(Text, primary_key=True)  # ex: PA1234
    score_participation: Mapped[Optional[float]] = mapped_column(Float)
    score_participation_specialite: Mapped[Optional[float]] = mapped_column(Float)
    score_loyaute: Mapped[Optional[float]] = mapped_column(Float)
    score_majorite: Mapped[Optional[float]] = mapped_column(Float)
    date_maj: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class DatanGroupe(Base):
    """Scores Datan par groupe parlementaire (source : data.gouv.fr / Datan)."""

    __tablename__ = "datan_groupes"

    libelle_abrev: Mapped[str] = mapped_column(Text, primary_key=True)  # ex: SOC, RN
    score_cohesion: Mapped[Optional[float]] = mapped_column(Float)
    score_participation: Mapped[Optional[float]] = mapped_column(Float)
    score_majorite: Mapped[Optional[float]] = mapped_column(Float)
    women_pct: Mapped[Optional[float]] = mapped_column(Float)
    age_moyen: Mapped[Optional[float]] = mapped_column(Float)
    score_rose: Mapped[Optional[float]] = mapped_column(Float)
    position_politique: Mapped[Optional[str]] = mapped_column(Text)
    date_maj: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class Amendement(Base):
    """Amendement déposé par un député."""

    __tablename__ = "amendements"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    numero: Mapped[Optional[str]] = mapped_column(String(20))
    titre: Mapped[Optional[str]] = mapped_column(Text)
    texte_legislature: Mapped[Optional[str]] = mapped_column(String(50))
    dossier_ref: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    date_depot: Mapped[Optional[date]] = mapped_column(Date, index=True)
    sort: Mapped[Optional[str]] = mapped_column(String(50))
    expose_sommaire: Mapped[Optional[str]] = mapped_column(Text)
    url_an: Mapped[Optional[str]] = mapped_column(String(500))
    depute_id: Mapped[Optional[str]] = mapped_column(ForeignKey("deputes.id"))
    legislature: Mapped[int] = mapped_column(Integer, default=17)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    depute: Mapped[Optional["Depute"]] = relationship(back_populates="amendements")
